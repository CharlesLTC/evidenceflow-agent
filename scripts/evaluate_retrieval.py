import argparse
import csv
import hashlib
import json
import os
import statistics
import time

import numpy as np

from evidenceflow.config import ROOT, Settings
from evidenceflow.document_store import DocumentStore
from evidenceflow.embeddings import OnnxEncoder
from evidenceflow.query_rewrite import AgentQueryRewrite
from evidenceflow.retriever import Retriever
from evidenceflow.trace_writer import utc_now, write_json


def metrics(rows):
    answerable = [r for r in rows if r["expected_doc_ids"]]
    n = len(answerable)
    result = {
        "sample_count": len(rows),
        "answerable_count": n,
        "unanswerable_count": len(rows) - n,
        "failed_queries": sum(bool(r.get("error")) for r in rows),
    }
    for k in (3, 5):
        per_query = [
            len(set(r["ranked_doc_ids"][:k]) & set(r["expected_doc_ids"]))
            / len(r["expected_doc_ids"])
            for r in answerable
        ]
        result[f"recall_at_{k}"] = {
            "value": sum(per_query) / n if n else None,
            "recall_sum": sum(per_query),
            "query_denominator": n,
            "relevant_retrieved": sum(
                len(set(r["ranked_doc_ids"][:k]) & set(r["expected_doc_ids"])) for r in answerable
            ),
            "relevant_total": sum(len(r["expected_doc_ids"]) for r in answerable),
        }
    reciprocal = [
        next(
            (1 / i for i, d in enumerate(r["ranked_doc_ids"][:5], 1) if d in r["expected_doc_ids"]),
            0,
        )
        for r in answerable
    ]
    result["mrr_at_5"] = {
        "value": sum(reciprocal) / n if n else None,
        "reciprocal_rank_sum": sum(reciprocal),
        "denominator": n,
    }
    result["ndcg_at_5"] = None  # No graded relevance annotations.
    times = [r["latency_ms"] for r in rows]
    result["mean_latency_ms"] = statistics.mean(times) if times else None
    result["p95_latency_ms"] = float(np.percentile(times, 95)) if times else None
    result["mean_model_calls"] = statistics.mean(r["model_calls"] for r in rows) if rows else None
    result["mean_tool_calls"] = statistics.mean(r["tool_calls"] for r in rows) if rows else None
    result["correct_abstention_rate"] = None  # Retrieval results are not QA refusals.
    return result


def token_cost(usage):
    in_price, out_price = (
        os.getenv("LLM_INPUT_USD_PER_MILLION"),
        os.getenv("LLM_OUTPUT_USD_PER_MILLION"),
    )
    if (
        not in_price
        or not out_price
        or "prompt_tokens" not in usage
        or "completion_tokens" not in usage
    ):
        return None
    return (
        usage["prompt_tokens"] * float(in_price) + usage["completion_tokens"] * float(out_price)
    ) / 1_000_000


def draw(report):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    charts = ROOT / "reports/charts"
    charts.mkdir(parents=True, exist_ok=True)
    completed = [(name, data) for name, data in report["strategies"].items() if data.get("metrics")]
    labels = [name for name, _ in completed]
    values = [data["metrics"]["recall_at_3"]["value"] for _, data in completed]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(labels, values, color=["#7187a3", "#478bb8", "#35a69b", "#e8a54b"][: len(values)])
    ax.bar_label(bars, fmt="%.3f")
    ax.set(
        ylim=(0, 1.1),
        ylabel="Macro Recall@3",
        title=f"Same frozen gold set: {report['answerable_queries']} answerable queries",
    )
    fig.tight_layout()
    fig.savefig(charts / "recall_at_3.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for (name, data), value in zip(completed, values, strict=True):
        calls = data["metrics"]["mean_model_calls"]
        ax.scatter(
            calls, value, s=100,
            label=f"{name}\n{data['metrics']['mean_latency_ms']:.1f} ms/query",
        )
    ax.set(
        xlabel="Model API calls per query",
        ylabel="Macro Recall@3",
        ylim=(0.85, 1.05),
        title="Retrieval quality vs model calls",
    )
    ax.grid(alpha=0.15)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(charts / "quality_cost.png", dpi=160)
    plt.close(fig)


def evaluate(include_dynamic=True):
    settings = Settings.from_env()
    questions = [
        json.loads(line)
        for line in (ROOT / "data/eval_questions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dataset_hashes = {
        f: hashlib.sha256((ROOT / "data" / f).read_bytes()).hexdigest()
        for f in ("documents.json", "eval_questions.jsonl", "gold_labels.json")
    }
    report = {
        "timestamp": utc_now(),
        "dataset_sha256": dataset_hashes,
        "documents": 32,
        "queries": len(questions),
        "answerable_queries": sum(bool(q["answerability"]) for q in questions),
        "timing_protocol": "CPU; encoder/index initialization excluded and separately timed; uncached query encoding; single query pass, no confidence intervals",
        "strategies": {},
    }
    store = DocumentStore(ROOT / "data/documents.json")
    report["documents"] = len(store.documents)
    init = time.perf_counter()
    try:
        encoder = OnnxEncoder()
        retriever = Retriever(store, encoder)
        retriever.dense("初始化索引")
        embedding_error = None
    except Exception as exc:
        encoder = None
        retriever = Retriever(store)
        embedding_error = type(exc).__name__
    report["initialization_ms"] = (time.perf_counter() - init) * 1000
    report["embedding_error"] = embedding_error
    all_rows, failures = [], []
    strategies = [
        ("A_BM25", "bm25"),
        ("B_Dense", "dense"),
        ("C_Hybrid_RRF", "hybrid"),
        ("D_Hybrid_AgentRewrite", "dynamic"),
    ]
    for name, strategy in strategies:
        blocker = embedding_error if strategy != "bm25" and embedding_error else None
        if strategy == "dynamic":
            blocker = (
                blocker
                or settings.live_blocker()
                or ("Dynamic evaluation not requested" if not include_dynamic else None)
            )
        if blocker:
            report["strategies"][name] = {
                "status": "BLOCKED",
                "blocker": blocker,
                "metrics": None,
                "cost_usd": None,
            }
            continue
        rows = []
        for q in questions:
            if encoder:
                encoder.memo.pop(q["question"], None)
            start = time.perf_counter()
            info = {"model_calls": 0, "tool_calls": 1, "usage": {}, "trace": None}
            error = None
            try:
                if strategy == "dynamic":
                    hits, info = AgentQueryRewrite(settings).retrieve(q["question"], retriever)
                else:
                    found = retriever.search(q["question"], top_k=10, strategy=strategy)
                    hits = found["hits"]
                    if "error" in found:
                        error = found["error"]
            except Exception as exc:
                hits, error = [], type(exc).__name__
            # Ranking metrics are by unique document, not repeated chunks.
            ids = list(dict.fromkeys(h["doc_id"] for h in hits))
            row = {
                "strategy": name,
                "id": q["id"],
                "question": q["question"],
                "expected_doc_ids": q["expected_doc_ids"],
                "ranked_doc_ids": ids,
                "latency_ms": (time.perf_counter() - start) * 1000,
                **info,
                "error": error,
                "cost_usd": token_cost(info["usage"]) if strategy == "dynamic" else 0.0,
            }
            rows.append(row)
            if error or (q["expected_doc_ids"] and not set(q["expected_doc_ids"]) <= set(ids[:3])):
                failures.append(row)
            print(f"{name} {q['id']} {'ERROR' if error else 'done'}", flush=True)
        m = metrics(rows)
        costs = [r["cost_usd"] for r in rows]
        report["strategies"][name] = {
            "status": "FAIL" if m["failed_queries"] else "PASS",
            "metrics": m,
            "cost_usd": sum(costs) if all(c is not None for c in costs) else None,
            "usage": {
                k: sum(r["usage"].get(k, 0) for r in rows)
                for k in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            if any(r["usage"] for r in rows)
            else None,
        }
        all_rows.extend(rows)
        write_json(ROOT / "reports/retrieval_progress.json", report)
    report["status"] = (
        "BLOCKED"
        if any(d["status"] == "BLOCKED" for d in report["strategies"].values())
        else "FAIL"
        if any(d["status"] == "FAIL" for d in report["strategies"].values())
        else "PASS"
    )
    write_json(ROOT / "reports/retrieval_metrics.json", report)
    write_json(ROOT / "reports/retrieval_details.json", all_rows)
    write_json(ROOT / "reports/retrieval_failures.json", failures)
    with (ROOT / "reports/retrieval_details.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "strategy",
            "id",
            "question",
            "expected_doc_ids",
            "ranked_doc_ids",
            "latency_ms",
            "model_calls",
            "tool_calls",
            "cost_usd",
            "error",
            "trace",
        ]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    draw(report)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--offline-only", action="store_true")
    args = p.parse_args()
    report = evaluate(not args.offline_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(2 if report["status"] == "BLOCKED" else 1 if report["status"] == "FAIL" else 0)
