import json

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import write_json


def validate(root=ROOT):
    report = json.loads((root / "reports/acceptance_results.live.json").read_text(encoding="utf-8"))
    errors = []
    if report["status"] != "PASS" or report["passed"] != 6:
        errors.append("Official live six have not all passed")
    traces = {}
    for row in report["cases"]:
        t = json.loads((root / row["trace"]).read_text(encoding="utf-8"))
        traces[row["id"]] = t
        output = json.loads((root / row["output"]).read_text(encoding="utf-8"))
        inp = json.loads((root / row["input"]).read_text(encoding="utf-8"))
        if t["mode"] != "live" or t["result"] != output or inp["question"] != output["question"]:
            errors.append(row["id"] + ": triplet mismatch")
        if not any(e["kind"] == "model_decision" and e["model_name"] for e in t["events"]):
            errors.append(row["id"] + ": no actual model decision recorded")
        if output["steps_used"] > 8 or output["tool_calls_used"] > 12:
            errors.append(row["id"] + ": budget exceeded")
    normal, fault = traces["TC01"], traces["TC06"]
    normal_actions = [e["tool_name"] for e in normal["events"] if e["kind"] == "tool_observation"]
    fault_actions = [e["tool_name"] for e in fault["events"] if e["kind"] == "tool_observation"]
    faults = [
        e
        for e in fault["events"]
        if e["kind"] == "tool_observation" and "error" in e["observation"]
    ]
    if normal_actions == fault_actions or not faults:
        errors.append("No different failure-observation path")
    if faults and not any(
        e["kind"] == "model_decision" and e["step"] > faults[0]["step"] for e in fault["events"]
    ):
        errors.append("No model decision after tool error")
    result = {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "model": report["model_name"],
        "six_passed": report["passed"],
        "normal": {"trace_id": normal["trace_id"], "tools": normal_actions},
        "failure_observation": {"trace_id": fault["trace_id"], "tools": fault_actions},
        "different_paths_verified": normal_actions != fault_actions and bool(faults),
        "citation_validity": report["citation_validity"],
    }
    write_json(root / "reports/live_branch_evidence.json", result)
    return result


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
