"""Frozen independent candidate-omission experiment; every injected alteration is explicit in Trace."""

import hashlib
import json
import statistics
import uuid
from dataclasses import replace

from evidenceflow.agent_graph import AgentService
from evidenceflow.config import ROOT, Settings
from evidenceflow.document_store import DocumentStore
from evidenceflow.evidence_guard import render_answer
from evidenceflow.schemas import AskRequest, Citation
from evidenceflow.trace_writer import utc_now, write_json


def transform_for(case, store):
    if not case["fault"]:
        return None

    def transform(draft, loaded):
        fault = case["fault"]
        clips = {
            "omit_duration": [("D03", "办公电脑申领须在IT门户填写申请")],
            "omit_training_deadline": [("D06", "完成信息安全培训。")],
            "omit_conflicting_values": [
                ("D01", "报销须附发票和出差审批单。"),
                ("D02", "报销须附发票和出差审批单。"),
            ],
            "omit_one_scope": [("D18", store.documents["D18"]["content"])],
        }
        citations = [
            Citation(
                doc_id=d,
                version_date=store.documents[d]["version_date"],
                chunk_id=d + "-C01",
                quote=quote,
            )
            for d, quote in clips[fault]
        ]
        if any(c.chunk_id not in loaded for c in citations):
            raise ValueError(
                "Evaluation fixture requires the model to read its quoted evidence first"
            )
        return draft.model_copy(
            update={
                "citations": citations,
                "facts": [],
                "answer": render_answer(draft.status, citations),
            }
        )

    return transform


def judge(case, result, events):
    checks = {
        "status": result.status == case["expected_status"],
        "documents": set(case["expected_doc_ids"]) <= {c.doc_id for c in result.citations},
        "facts": all(f in result.answer for f in case["expected_facts"]),
        "bounded": result.steps_used <= 8 and result.tool_calls_used <= 12,
    }
    reads = {
        c["chunk_id"]: (c["text"], e["observation"]["version_date"])
        for e in events
        if e.get("tool_name") == "read_document" and "chunks" in e["observation"]
        for c in e["observation"]["chunks"]
    }
    invalid = sum(
        c.chunk_id not in reads
        or c.quote not in reads[c.chunk_id][0]
        or c.version_date != reads[c.chunk_id][1]
        for c in result.citations
    )
    checks["citations"] = invalid == 0
    if case["expected_status"] == "NEEDS_CLARIFICATION":
        checks["unresolved"] = bool(result.missing_info) and any(
            c["resolution"] == "UNRESOLVED" for c in result.conflicts
        )
    return checks, invalid


def main():
    fixture = ROOT / "data/critic_eval.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    settings = replace(Settings.from_env(), strategy="bm25", critic_enabled=False)
    run_id = uuid.uuid4().hex
    rows = []
    report = {
        "run_id": run_id,
        "started_at": utc_now(),
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "protocol": "6 fixed cases: 4 controlled omissions and 2 clean controls. Only the first real model submission is transformed, visibly labelled candidate_injection; this is not a natural error-rate estimate. Baseline and Critic use the same fixture and unchanged external criteria.",
        "cases": rows,
    }
    for case in cases:
        pair = {"id": case["id"], "question": case["question"], "fault": case["fault"]}
        for enabled in (False, True):
            store = DocumentStore(ROOT / "data/documents.json")
            service = AgentService(
                settings, store=store, candidate_transform=transform_for(case, store)
            )
            result = service.ask(
                AskRequest(question=case["question"], mode="live", enable_critic=enabled)
            )
            path = f"examples/traces/live/{result.trace_id}.json"
            events = json.loads((ROOT / path).read_text(encoding="utf-8"))["events"]
            checks, invalid = judge(case, result, events)
            pair["critic" if enabled else "baseline"] = {
                "correct": all(checks.values()),
                "checks": checks,
                "result_status": result.status,
                "trace": path,
                "steps": result.steps_used,
                "tool_calls": result.tool_calls_used,
                "usage": result.usage,
                "latency_ms": result.latency_ms,
                "critic": result.critic,
                "invalid_citations": invalid,
                "injection_events": sum(e["kind"] == "candidate_injection" for e in events),
            }
            service.sessions.close()
            print(
                f"{case['id']} critic={enabled}: correct={all(checks.values())} state={result.status}",
                flush=True,
            )
        rows.append(pair)
        write_json(ROOT / f"reports/critic_eval_runs/{run_id}.json", report)
    wrong = [r for r in rows if r["fault"] and not r["baseline"]["correct"]]
    corrected = sum(r["critic"]["correct"] for r in wrong)
    new_errors = sum(r["baseline"]["correct"] and not r["critic"]["correct"] for r in rows)
    clean_false_revisions = sum(
        not r["fault"] and r["critic"]["critic"]["revisions_requested"] > 0 for r in rows
    )
    report.update(
        {
            "finished_at": utc_now(),
            "total": len(rows),
            "injected_cases": sum(bool(r["fault"]) for r in rows),
            "baseline_correct": sum(r["baseline"]["correct"] for r in rows),
            "critic_correct": sum(r["critic"]["correct"] for r in rows),
            "correction_success": {
                "numerator": corrected,
                "denominator": len(wrong),
                "rate": corrected / len(wrong) if wrong else None,
            },
            "new_final_errors": new_errors,
            "clean_control_false_revisions": clean_false_revisions,
            "invalid_final_citations": sum(r["critic"]["invalid_citations"] for r in rows),
            "mean_extra_model_steps": statistics.mean(
                r["critic"]["steps"] - r["baseline"]["steps"] for r in rows
            ),
            "mean_critic_api_calls": statistics.mean(
                r["critic"]["critic"]["model_calls"] for r in rows
            ),
            "mean_extra_latency_ms": statistics.mean(
                r["critic"]["latency_ms"] - r["baseline"]["latency_ms"] for r in rows
            ),
            "mean_critic_latency_ms": statistics.mean(
                r["critic"]["critic"]["latency_ms"] for r in rows
            ),
            "extra_tokens": sum(
                r["critic"]["usage"].get("total_tokens", 0)
                - r["baseline"]["usage"].get("total_tokens", 0)
                for r in rows
            ),
            "cost_usd": None,
            "status": "PASS"
            if all(r["critic"]["correct"] for r in rows)
            and new_errors == 0
            and clean_false_revisions == 0
            else "FAIL",
        }
    )
    write_json(ROOT / f"reports/critic_eval_runs/{run_id}.json", report)
    write_json(ROOT / "reports/critic_evaluation.json", report)
    print(
        json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2)
    )
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
