"""Recompute quality evidence from saved results and actual Trace, without new model calls."""

import argparse
import hashlib
import json

from evidenceflow.config import ROOT
from evidenceflow.schemas import Answer
from evidenceflow.trace_writer import utc_now, write_json
from scripts.evaluate_critic import judge


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def verify(scope="all"):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    if scope in ("all", "core"):
        for strategy in ("bm25", "hybrid"):
            report = read(f"reports/quality/{strategy}_official.json")
            check(
                report["status"] == "PASS" and report["passed"] == report["total"] == 6,
                strategy + " official six failed",
            )
        stability = read("reports/quality/tc02_stability.json")
        check(stability["total"] == len(stability["runs"]) == 5, "TC02 denominator changed")
        for row in stability["runs"]:
            trace = read(row["trace"])
            submissions = [e for e in trace["events"] if e.get("tool_name") == "submit_answer"]
            rejections = sum(not e["observation"].get("valid", False) for e in submissions)
            check(rejections == row["guard_rejections"], "TC02 recorded rejection count mismatch")
            result = trace["result"]
            check(
                row["status"] == "PASS"
                and result["status"] == "NEEDS_CLARIFICATION"
                and {"D01", "D02"} <= {c["doc_id"] for c in result["citations"]}
                and "30天" in result["answer"]
                and "15天" in result["answer"]
                and result["missing_info"],
                "TC02 original assertions failed",
            )
        check(
            read("reports/quality/hybrid_execution.json")["status"] == "PASS",
            "No actual Hybrid coverage",
        )
        check(
            read("reports/quality/hybrid_fallback_live.json")["status"] == "PASS",
            "Live BM25 fallback failed",
        )
        check(
            read("reports/extended_live.json")["status"] == "PASS",
            "Latest exceptional live suite failed",
        )
        # Basis captions are audited on fresh traces, historical immutable traces are not rewritten.
        traces = [row["trace"] for row in read("reports/quality/hybrid_official.json")["cases"]]
        for path in traces:
            events = read(path)["events"]
            by_step = {e["step"]: e for e in events}
            for event in events:
                if event["kind"] == "model_decision":
                    check(
                        event.get("decision_basis_source") == "observable_events",
                        "Unattributed decision basis",
                    )
                    check(
                        all(
                            s < event["step"] and by_step[s]["kind"] == "tool_observation"
                            for s in event.get("basis_event_steps", [])
                        ),
                        "Invalid basis event reference",
                    )
    if scope in ("all", "critic"):
        report = read("reports/critic_evaluation.json")
        fixture = read("data/critic_eval.json")
        expected = {c["id"]: c for c in fixture}
        check(
            hashlib.sha256((ROOT / "data/critic_eval.json").read_bytes()).hexdigest()
            == report["fixture_sha256"],
            "Critic fixture changed",
        )
        check(len(report["cases"]) == len(fixture) == 6, "Critic denominator changed")
        for row in report["cases"]:
            for arm in ("baseline", "critic"):
                record = row[arm]
                trace = read(record["trace"])
                result = Answer.model_validate(trace["result"])
                checks, invalid = judge(expected[row["id"]], result, trace["events"])
                check(
                    record["correct"] == all(checks.values())
                    and record["invalid_citations"] == invalid,
                    "Critic correctness does not match actual Trace",
                )
                counted = sum(
                    e["kind"] in ("model_decision", "model_error") for e in trace["events"]
                ) + sum(
                    e["review"]["model_steps"]
                    for e in trace["events"]
                    if e["kind"] == "critic_review"
                )
                check(
                    counted == result.steps_used and counted <= 8,
                    "Critic model budget/count mismatch",
                )
        wrong = [r for r in report["cases"] if r["fault"] and not r["baseline"]["correct"]]
        check(
            report["correction_success"]["denominator"] == len(wrong)
            and report["correction_success"]["numerator"]
            == sum(r["critic"]["correct"] for r in wrong),
            "Critic correction metric mismatch",
        )
        check(report["status"] == "PASS", "Latest critic omission experiment failed")
        official = read("reports/quality/bm25_critic_official.json")
        check(
            official["status"] == "PASS" and official["passed"] == 6,
            "Critic-enabled official six failed",
        )
    output = {
        "status": "FAIL" if errors else "PASS",
        "scope": scope,
        "timestamp": utc_now(),
        "errors": errors,
    }
    write_json(ROOT / f"reports/quality/verification_{scope}.json", output)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return not errors


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--scope", choices=["all", "core", "critic"], default="all")
    raise SystemExit(0 if verify(p.parse_args().scope) else 1)
