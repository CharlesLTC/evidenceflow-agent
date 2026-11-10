import json

from evidenceflow.schemas import AskRequest


def events(s, result):
    p = s.settings.root / f"examples/traces/{result.mode}/{result.trace_id}.json"
    return json.loads(p.read_text(encoding="utf-8"))["events"]


def test_tc06_error_then_simulator_decides_recovery(service_factory):
    s = service_factory()
    result = s.ask(AskRequest(question="办公电脑申领审批需要多久？", mode="mock", fail_search_count=1))
    assert result.status == "COMPLETED"
    e = events(s, result)
    error = next(x for x in e if x["kind"] == "tool_observation" and "error" in x["observation"])
    assert any(x["kind"] == "model_decision" and x["step"] > error["step"] for x in e)


def test_tc12_repeated_error_terminates_honestly(service_factory):
    s = service_factory()
    result = s.ask(AskRequest(question="办公电脑申领审批需要多久？", mode="mock", fail_search_count=2))
    assert result.status == "FAILED"
    assert not result.citations
    assert sum(x["kind"] == "tool_observation" and "error" in x["observation"] for x in events(s, result)) == 2

