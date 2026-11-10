import json

from evidenceflow.llm_client import ScriptedModel, call
from evidenceflow.schemas import AskRequest
from evidenceflow.tools import tool_schemas
from tests.test_agent_graph import citation, submit, trace


def test_structured_submission_renders_without_relaxing_guard(service_factory):
    c = citation()
    model = ScriptedModel(
        [
            call("read_document", doc_id="D03"),
            call("submit_answer", status="COMPLETED", citations=[c.model_dump()], missing_info=[]),
        ]
    )
    service = service_factory(model)
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model"))
    assert result.status == "COMPLETED" and result.answer == "D03：" + c.quote
    observations = [
        e for e in trace(service, result)["events"] if e.get("tool_name") == "submit_answer"
    ]
    assert len(observations) == 1 and observations[0]["observation"]["valid"]
    assert "answer" not in observations[0]["arguments"]


def test_structured_submission_still_rejects_fabricated_quote(service_factory):
    c = citation().model_dump() | {"quote": "申领只需99天。"}

    def revise(messages):
        assert any(
            e.startswith("QUOTE_NOT_EXACT") for e in json.loads(messages[-1]["content"])["errors"]
        )
        return submit()

    service = service_factory(
        ScriptedModel(
            [
                call("read_document", doc_id="D03"),
                call("submit_answer", status="COMPLETED", citations=[c], missing_info=[]),
                revise,
            ]
        )
    )
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model"))
    assert result.status == "COMPLETED" and "99" not in result.answer


def test_hybrid_default_is_executed_and_failure_is_observed_before_model_fallback(service_factory):
    def fallback(messages):
        obs = json.loads(messages[-1]["content"])
        assert obs["executed_strategy"] == "hybrid"
        assert obs["error"]["code"] == "RETRIEVAL_UNAVAILABLE"
        assert obs["fallback_options"] == ["bm25"]
        return call("search_documents", query="电脑申领", strategy="bm25")

    service = service_factory(
        ScriptedModel(
            [
                call("search_documents", query="电脑申领"),
                fallback,
                call("read_document", doc_id="D03"),
                submit(),
            ]
        ),
        strategy="hybrid",
    )
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model"))
    assert result.status == "COMPLETED"
    searches = [
        e for e in trace(service, result)["events"] if e.get("tool_name") == "search_documents"
    ]
    assert [e["observation"]["executed_strategy"] for e in searches] == ["hybrid", "bm25"]
    assert (
        tool_schemas("hybrid")[0]["function"]["parameters"]["properties"]["strategy"]["default"]
        == "hybrid"
    )


def test_decision_basis_points_to_actual_timeout_observation(service_factory):
    service = service_factory()
    result = service.ask(AskRequest(question="电脑审批多久", mode="mock", fail_search_count=1))
    events = trace(service, result)["events"]
    error = next(
        e
        for e in events
        if e.get("tool_name") == "search_documents" and "error" in e["observation"]
    )
    decision = next(
        e for e in events if e["kind"] == "model_decision" and e["step"] > error["step"]
    )
    assert "TOOL_TIMEOUT" in decision["decision_basis"] and "重新检索" in decision["decision_basis"]
    assert decision["basis_event_steps"] == [error["step"]]
    assert len({e["decision_basis"] for e in events if "decision_basis" in e}) >= 4
