import json

import httpx
import pytest

from evidenceflow.config import Settings
from evidenceflow.evidence_guard import render_answer
from evidenceflow.llm_client import Decision, LiveModel, ModelError, ScriptedModel, call
from evidenceflow.schemas import AskRequest, Citation


def citation():
    return Citation(
        doc_id="D03",
        version_date="2025-01-01",
        chunk_id="D03-C01",
        quote="办公电脑申领须在IT门户填写申请，经主管审批后3个工作日内完成。",
    )


def submit():
    c = citation()
    return call(
        "submit_answer",
        status="COMPLETED",
        answer=render_answer("COMPLETED", [c]),
        citations=[c.model_dump()],
        missing_info=[],
    )


def trace(service, result):
    return json.loads(
        (service.settings.root / f"examples/traces/{result.mode}/{result.trace_id}.json").read_text(
            encoding="utf-8"
        )
    )


def test_fake_model_observation_changes_next_action(service_factory):
    def respond(messages):
        observation = json.loads(messages[-1]["content"])
        return (
            call("search_documents", query="电脑申领", top_k=8)
            if "error" in observation
            else call("read_document", doc_id="D03")
        )

    normal = ScriptedModel([call("search_documents", query="电脑"), respond, submit()])
    s = service_factory(normal)
    out = s.ask(AskRequest(question="电脑审批多久", mode="fake_model"))
    assert out.status == "COMPLETED"
    assert [e["tool_name"] for e in trace(s, out)["events"] if e["kind"] == "tool_observation"] == [
        "search_documents",
        "read_document",
        "submit_answer",
    ]
    fault = ScriptedModel(
        [
            call("search_documents", query="电脑"),
            respond,
            call("read_document", doc_id="D03"),
            submit(),
        ]
    )
    s2 = service_factory(fault)
    out2 = s2.ask(AskRequest(question="电脑审批多久", mode="fake_model", fail_search_count=1))
    assert out2.status == "COMPLETED"
    assert [
        e["tool_name"] for e in trace(s2, out2)["events"] if e["kind"] == "tool_observation"
    ] == ["search_documents", "search_documents", "read_document", "submit_answer"]
    assert json.loads(fault.seen[1][-1]["content"])["error"]["code"] == "TOOL_TIMEOUT"


def test_model_budget_stops_without_extra_call(service_factory):
    model = ScriptedModel([call("search_documents", query="电脑")] * 9)
    s = service_factory(model)
    result = s.ask(AskRequest(question="Q", mode="fake_model"))
    assert result.status == "INCOMPLETE"
    assert result.steps_used == result.tool_calls_used == 8
    assert len(model.seen) == 8


def test_parallel_tool_calls_counted_and_bound(service_factory):
    decision = Decision(
        [{"id": str(i), "name": "read_document", "arguments": {"doc_id": "D03"}} for i in range(15)]
    )
    s = service_factory(ScriptedModel([decision]))
    out = s.ask(AskRequest(question="Q", mode="fake_model"))
    assert out.status == "INCOMPLETE"
    assert out.tool_calls_used == 12 and out.steps_used == 1
    assert len([e for e in trace(s, out)["events"] if e["kind"] == "tool_observation"]) == 12


def test_guard_rejection_is_observed_before_revision(service_factory):
    bad = submit()
    bad.tool_calls[0]["arguments"]["citations"][0]["quote"] = "主管审批后99个工作日内完成。"

    def revise(messages):
        assert "QUOTE_NOT_EXACT:D03-C01" in json.loads(messages[-1]["content"])["errors"]
        return submit()

    s = service_factory(ScriptedModel([call("read_document", doc_id="D03"), bad, revise]))
    result = s.ask(AskRequest(question="Q", mode="fake_model"))
    assert result.status == "COMPLETED" and "99" not in result.answer


def test_missing_live_key_never_falls_back_to_mock(service_factory):
    s = service_factory()
    result = s.ask(AskRequest(question="Q", mode="live"))
    assert result.status == "FAILED" and result.error_code == "BLOCKED_LIVE"
    assert result.mode == "live" and result.tool_calls_used == 0
    assert not any(e["kind"] == "model_decision" for e in trace(s, result)["events"])


def test_mode_mismatch_is_rejected(service_factory):
    with pytest.raises(ValueError, match="mode"):
        service_factory(ScriptedModel([])).ask(AskRequest(question="Q", mode="live"))


def test_live_adapter_transports_real_tool_messages_and_usage():
    observed = []

    def handler(request):
        observed.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "function": {
                                        "name": "search_documents",
                                        "arguments": '{"query":"电脑"}',
                                    },
                                }
                            ]
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
            },
        )

    m = LiveModel(
        Settings(api_key="unit-test-placeholder", model_name="transport-double"),
        httpx.MockTransport(handler),
    )
    d = m.decide([{"role": "user", "content": "Q"}], [])
    assert d.tool_calls[0]["arguments"]["query"] == "电脑"
    assert d.usage["total_tokens"] == 15
    assert observed[0]["tool_choice"] == "required"


@pytest.mark.parametrize("status", [401, 429, 500])
def test_model_http_error_does_not_log_response_body(status):
    model = LiveModel(
        Settings(api_key="unit-test-placeholder", model_name="test"),
        httpx.MockTransport(lambda r: httpx.Response(status, text="private response")),
    )
    with pytest.raises(ModelError, match=f"MODEL_HTTP_{status}"):
        model.decide([], [])
