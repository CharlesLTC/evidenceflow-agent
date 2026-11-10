import argparse
import json
import uuid

from evidenceflow.agent_graph import AgentService
from evidenceflow.schemas import AskRequest
from evidenceflow.trace_writer import utc_now, write_json

CASES = [
    ("TC01", "办公电脑申领审批需要多久？"),
    ("TC02", "差旅报销期限是多久？"),
    ("TC03", "公司的年终奖金是多少？"),
    ("TC04", "领电脑一般几天能批下来？"),
    ("TC05", "那多久批下来？"),
    ("TC06", "办公电脑申领审批需要多久？"),
]


def assess(case_id, result, trace, service, pre_result=None):
    checks = {"schema": True, "mode_consistent": trace["mode"] == result.mode}
    ids = {c.doc_id for c in result.citations}
    if case_id in ("TC01", "TC04", "TC05"):
        checks.update(
            completed=result.status == "COMPLETED",
            correct_document="D03" in ids,
            expected_fact="3个工作日" in result.answer,
        )
    if case_id == "TC02":
        checks.update(
            clarification=result.status == "NEEDS_CLARIFICATION",
            both_versions={"D01", "D02"} <= ids,
            both_values="30天" in result.answer and "15天" in result.answer,
            unresolved=any(c["resolution"] == "UNRESOLVED" for c in result.conflicts),
            asks_for_context=bool(result.missing_info),
        )
    if case_id == "TC03":
        checks.update(
            abstention=result.status == "INSUFFICIENT_EVIDENCE",
            no_false_citation=not result.citations,
        )
    if case_id == "TC05":
        checks.update(
            context_precondition=pre_result is not None and pre_result.status == "COMPLETED",
            same_session=pre_result is not None and pre_result.session_id == result.session_id,
        )
    if case_id == "TC06":
        errors = [
            e
            for e in trace["events"]
            if e["kind"] == "tool_observation" and "error" in e["observation"]
        ]
        checks.update(
            controlled_state=result.status in ("COMPLETED", "FAILED"),
            tool_error_observed=bool(errors),
            decision_after_error=any(
                e["kind"] == "model_decision" and e["step"] > errors[0]["step"]
                for e in trace["events"]
            )
            if errors
            else False,
            honest_success=result.status != "COMPLETED"
            or ("D03" in ids and "3个工作日" in result.answer),
        )
    reads = {
        c["chunk_id"]
        for e in trace["events"]
        if e["kind"] == "tool_observation"
        and e["tool_name"] == "read_document"
        and "chunks" in e["observation"]
        for c in e["observation"]["chunks"]
    }
    valid = sum(
        c.chunk_id in reads
        and c.chunk_id in service.store.chunks
        and c.quote in service.store.chunks[c.chunk_id]["text"]
        and c.version_date == service.store.documents[c.doc_id]["version_date"]
        for c in result.citations
    )
    checks["all_citations_valid"] = valid == len(result.citations)
    return checks, valid


def run(mode="mock", service=None):
    service = service or AgentService()
    root = service.settings.root
    blocker = service.settings.live_blocker() if mode == "live" else None
    rows, citation_total, citation_valid = [], 0, 0
    for case_id, question in CASES:
        session = "accept_" + uuid.uuid4().hex
        pre = None
        if case_id == "TC05":
            pre = service.ask(AskRequest(question="电脑怎么申领？", session_id=session, mode=mode))
        request = AskRequest(
            question=question,
            session_id=session,
            mode=mode,
            fail_search_count=1 if case_id == "TC06" else 0,
        )
        result = service.ask(request)
        path = f"examples/traces/{mode}/{result.trace_id}.json"
        trace = json.loads((root / path).read_text(encoding="utf-8"))
        checks, valid = assess(case_id, result, trace, service, pre)
        citation_total += len(result.citations)
        citation_valid += valid
        actual_model_decisions = sum(e["kind"] == "model_decision" for e in trace["events"])
        status = (
            "BLOCKED"
            if blocker or result.error_code == "BLOCKED_LIVE"
            else "PASS"
            if all(checks.values())
            else "FAIL"
        )
        rows.append(
            {
                "id": case_id,
                "question": question,
                "status": status,
                "result_status": result.status,
                "checks": checks,
                "trace": path,
                "output": f"examples/outputs/{mode}/{result.trace_id}.json",
                "input": f"examples/inputs/{mode}-{result.trace_id}.json",
                "model_decisions": actual_model_decisions,
                "tools": [
                    e["tool_name"] for e in trace["events"] if e["kind"] == "tool_observation"
                ],
                "pre_trace": f"examples/traces/{mode}/{pre.trace_id}.json" if pre else None,
            }
        )
    branches = {tuple(r["tools"]) for r in rows if r["status"] == "PASS" and r["model_decisions"]}
    summary = {
        "timestamp": utc_now(),
        "mode": mode,
        "model_name": rows and result.model_name,
        "status": "BLOCKED"
        if blocker
        else "PASS"
        if all(r["status"] == "PASS" for r in rows)
        else "FAIL",
        "blocker": blocker,
        "passed": sum(r["status"] == "PASS" for r in rows),
        "total": len(rows),
        "citation_validity": {
            "numerator": citation_valid,
            "denominator": citation_total,
            "rate": citation_valid / citation_total if citation_total else None,
        },
        "live_branch_count": len(branches) if mode == "live" else 0,
        "cases": rows,
    }
    write_json(root / f"reports/acceptance_results.{mode}.json", summary)
    index_path = root / "reports/acceptance_results.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index[mode] = {
        "path": f"reports/acceptance_results.{mode}.json",
        "status": summary["status"],
        "passed": summary["passed"],
        "total": summary["total"],
    }
    write_json(index_path, index)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["live", "mock"], default="live")
    args = parser.parse_args()
    report = run(args.mode)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(2 if report["status"] == "BLOCKED" else 1 if report["status"] == "FAIL" else 0)
