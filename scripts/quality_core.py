"""Unchanged official assertions plus explicit five-run conflict and Hybrid-use evidence."""

import argparse
import json
import uuid
from dataclasses import replace

from evidenceflow.agent_graph import AgentService
from evidenceflow.config import ROOT, Settings
from evidenceflow.schemas import AskRequest
from evidenceflow.trace_writer import utc_now, write_json
from scripts.run_acceptance import assess, run


def archive_current():
    directory = ROOT / f"reports/logs/attempts/quality-start-{uuid.uuid4().hex}"
    for name in (
        "acceptance_results.json",
        "acceptance_results.live.json",
        "acceptance_results.mock.json",
    ):
        path = ROOT / "reports" / name
        if path.exists():
            write_json(directory / name, json.loads(path.read_text(encoding="utf-8")))


def single_conflict(service):
    result = service.ask(AskRequest(question="差旅报销期限是多久？", mode="live"))
    trace_path = f"examples/traces/live/{result.trace_id}.json"
    trace = json.loads((ROOT / trace_path).read_text(encoding="utf-8"))
    checks, _ = assess("TC02", result, trace, service)
    submissions = [e for e in trace["events"] if e.get("tool_name") == "submit_answer"]
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "trace": trace_path,
        "input": f"examples/inputs/live-{result.trace_id}.json",
        "output": f"examples/outputs/live/{result.trace_id}.json",
        "result_status": result.status,
        "submission_attempts": len(submissions),
        "guard_rejections": sum(not e["observation"].get("valid", False) for e in submissions),
        "first_submission_valid": bool(submissions)
        and submissions[0]["observation"].get("valid", False),
        "usage": result.usage,
        "latency_ms": result.latency_ms,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=["bm25", "hybrid"], required=True)
    parser.add_argument("--conflict-repeats", type=int, default=0)
    parser.add_argument("--fallback-probe", action="store_true")
    args = parser.parse_args()
    archive_current()
    settings = replace(Settings.from_env(), strategy=args.strategy)
    service = AgentService(settings)
    report = run("live", service)
    tag = f"{args.strategy}_{'critic_' if settings.critic_enabled else ''}official"
    write_json(ROOT / f"reports/quality/runs/{uuid.uuid4().hex}-{tag}.json", report)
    write_json(ROOT / f"reports/quality/{tag}.json", report)
    print(
        f"{args.strategy} official: {report['status']} {report['passed']}/{report['total']}",
        flush=True,
    )
    failures = report["status"] != "PASS"
    if args.strategy == "hybrid":
        cases = []
        for row in report["cases"]:
            paths = [row["trace"]] + ([row["pre_trace"]] if row["pre_trace"] else [])
            events = [
                e
                for p in paths
                for e in json.loads((ROOT / p).read_text(encoding="utf-8"))["events"]
                if e.get("tool_name") == "search_documents"
            ]
            cases.append(
                {
                    "id": row["id"],
                    "official_status": row["status"],
                    "attempted_hybrid": any(
                        e["arguments"].get("strategy", args.strategy) == "hybrid" for e in events
                    ),
                    "successful_hybrid_searches": sum(
                        e["observation"].get("executed_strategy") == "hybrid"
                        and "error" not in e["observation"]
                        for e in events
                    ),
                    "search_strategies": [
                        e["observation"].get(
                            "executed_strategy", e["observation"].get("attempted_strategy")
                        )
                        for e in events
                    ],
                    "traces": paths,
                }
            )
        coverage = {
            "status": "PASS"
            if not failures
            and all(c["attempted_hybrid"] for c in cases)
            and any(c["successful_hybrid_searches"] for c in cases)
            else "FAIL",
            "cases": cases,
            "criterion": "All official assertions unchanged; every case attempts Hybrid (TC05 includes setup turn), with successful Hybrid execution; timeout recovery may explicitly use BM25.",
        }
        coverage_name = (
            "hybrid_critic_execution.json" if settings.critic_enabled else "hybrid_execution.json"
        )
        write_json(ROOT / "reports/quality" / coverage_name, coverage)
        failures |= coverage["status"] != "PASS"
    if args.conflict_repeats:
        rows = []
        for i in range(args.conflict_repeats):
            row = single_conflict(service)
            row["run"] = i + 1
            rows.append(row)
            print(
                f"TC02 run {i + 1}: {row['status']}, guard_rejections={row['guard_rejections']}",
                flush=True,
            )
        baseline = json.loads((ROOT / "reports/quality/baseline.json").read_text(encoding="utf-8"))
        passed = sum(r["status"] == "PASS" for r in rows)
        mean_rejections = sum(r["guard_rejections"] for r in rows) / len(rows)
        summary = {
            "timestamp": utc_now(),
            "status": "PASS"
            if passed == len(rows) and mean_rejections < baseline["guard_rejections"]
            else "FAIL",
            "passed": passed,
            "total": len(rows),
            "success_rate": passed / len(rows),
            "first_submission_success_rate": sum(r["first_submission_valid"] for r in rows)
            / len(rows),
            "baseline_guard_rejections": baseline["guard_rejections"],
            "mean_guard_rejections": mean_rejections,
            "runs": rows,
            "criteria": "Five consecutive live runs, unchanged TC02 assertions; no run discarded or retried externally.",
        }
        write_json(ROOT / "reports/quality/tc02_stability.json", summary)
        failures |= summary["status"] != "PASS"
    if args.fallback_probe:
        fallback = AgentService(replace(settings, strategy="hybrid"))
        fallback.retriever.encoder = None
        fallback.retriever.vectors = None
        result = fallback.ask(AskRequest(question="办公电脑申领审批需要多久？", mode="live"))
        trace_path = f"examples/traces/live/{result.trace_id}.json"
        events = json.loads((ROOT / trace_path).read_text(encoding="utf-8"))["events"]
        searches = [e for e in events if e.get("tool_name") == "search_documents"]
        failed = any(
            e["observation"].get("error", {}).get("code") == "RETRIEVAL_UNAVAILABLE"
            for e in searches
        )
        recovered = any(
            e["observation"].get("executed_strategy") == "bm25" and "error" not in e["observation"]
            for e in searches
        )
        status = (
            "PASS"
            if failed
            and recovered
            and result.status == "COMPLETED"
            and "3个工作日" in result.answer
            else "FAIL"
        )
        write_json(
            ROOT / "reports/quality/hybrid_fallback_live.json",
            {
                "status": status,
                "trace": trace_path,
                "injection": "semantic backend deliberately unavailable; no automatic tool retry",
                "result_status": result.status,
                "observed_unavailable": failed,
                "model_chose_bm25": recovered,
            },
        )
        failures |= status != "PASS"
        fallback.sessions.close()
    service.sessions.close()
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
