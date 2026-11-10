import json

import pytest
from pydantic import ValidationError

from evidenceflow.config import Settings
from evidenceflow.evidence_critic import CriticVerdict, EvidenceCritic
from evidenceflow.llm_client import Decision, ScriptedModel, call
from evidenceflow.schemas import AskRequest
from tests.test_agent_graph import citation, submit, trace


def review(verdict="PASS"):
    return call(
        "review_evidence",
        verdict=verdict,
        issue_codes=["MISSING_RELEVANT_FACT"] if verdict == "REVISE" else [],
        document_ids=["D03"] if verdict == "REVISE" else [],
    )


def partial_submission():
    c = citation().model_dump() | {"quote": "办公电脑申领须在IT门户填写申请"}
    return call("submit_answer", status="COMPLETED", citations=[c], missing_info=[])


def test_critic_disabled_keeps_existing_behavior_and_spends_no_review_calls(service_factory):
    service = service_factory(ScriptedModel([call("read_document", doc_id="D03"), submit()]))
    critic_model = ScriptedModel([])
    service.critic_model = critic_model
    result = service.ask(
        AskRequest(question="电脑审批多久", mode="fake_model", enable_critic=False)
    )
    assert result.status == "COMPLETED" and result.steps_used == 2
    assert not result.critic["enabled"] and result.critic["reviews"] == 0 and not critic_model.seen


def test_independent_review_feedback_drives_model_repair_and_counts_shared_budget(service_factory):
    def revise(messages):
        obs = json.loads(messages[-1]["content"])
        assert obs["guard_valid"] and not obs["valid"]
        assert obs["critic"]["verdict"] == "REVISE"
        return submit()

    service = service_factory(
        ScriptedModel([call("read_document", doc_id="D03"), partial_submission(), revise])
    )
    service.critic_model = ScriptedModel([review("REVISE"), review()])
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model", enable_critic=True))
    assert result.status == "COMPLETED" and "3个工作日" in result.answer
    assert result.steps_used == 5 and result.tool_calls_used == 3
    assert result.critic["reviews"] == 2 and result.critic["revisions_requested"] == 1
    events = trace(service, result)["events"]
    assert len([e for e in events if e["kind"] == "critic_review"]) == 2


def test_critic_can_never_approve_a_guard_invalid_quote(service_factory):
    bad = submit()
    bad.tool_calls[0]["arguments"]["citations"][0]["quote"] = "申领审批只需99天。"
    critic_model = ScriptedModel([review()])

    def revise(messages):
        assert not critic_model.seen
        assert any(
            e.startswith("QUOTE_NOT_EXACT") for e in json.loads(messages[-1]["content"])["errors"]
        )
        return submit()

    service = service_factory(ScriptedModel([call("read_document", doc_id="D03"), bad, revise]))
    service.critic_model = critic_model
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model", enable_critic=True))
    assert result.status == "COMPLETED" and "99" not in result.answer
    assert len(critic_model.seen) == 1


def test_critic_repeated_rejection_stops_after_one_repair(service_factory):
    service = service_factory(
        ScriptedModel(
            [call("read_document", doc_id="D03"), partial_submission(), partial_submission()]
        )
    )
    service.critic_model = ScriptedModel([review("REVISE"), review("REVISE")])
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model", enable_critic=True))
    assert result.status == "INCOMPLETE" and result.error_code == "CRITIC_REPAIR_LIMIT"
    assert result.critic["reviews"] == 2 and result.steps_used <= 8


def test_critic_cannot_make_a_ninth_or_over_budget_call(service_factory):
    service = service_factory(ScriptedModel([call("read_document", doc_id="D03"), submit()]))
    critic_model = ScriptedModel([review()])
    service.critic_model = critic_model
    result = service.ask(
        AskRequest(
            question="电脑审批多久", mode="fake_model", enable_critic=True, max_model_steps=2
        )
    )
    assert result.status == "INCOMPLETE" and result.steps_used == 2 and not critic_model.seen


def test_unavailable_critic_is_controlled_failure(service_factory):
    service = service_factory(ScriptedModel([call("read_document", doc_id="D03"), submit()]))
    service.critic_model = ScriptedModel([])
    result = service.ask(AskRequest(question="电脑审批多久", mode="fake_model", enable_critic=True))
    assert result.status == "FAILED" and result.error_code == "CRITIC_UNAVAILABLE"


def test_verdict_is_bounded_and_never_accepts_hidden_reasoning_fields():
    with pytest.raises(ValidationError):
        CriticVerdict(verdict="PASS", issue_codes=["WRONG_SCOPE"])
    with pytest.raises(ValidationError):
        CriticVerdict(
            verdict="REVISE", issue_codes=["WRONG_SCOPE"], hidden_reasoning="not accepted"
        )
    with pytest.raises(ValueError, match="mode"):
        EvidenceCritic(Settings(), "live", ScriptedModel([]))


def test_invalid_critic_response_retains_available_usage_without_input_or_reasoning():
    d = call("review_evidence", verdict="PASS", issue_codes=["WRONG_SCOPE"], document_ids=[])
    d = Decision(d.tool_calls, {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8})
    critic = EvidenceCritic(Settings(), "fake_model", ScriptedModel([d]))
    result = critic.review({"question": "Q"})
    assert result["verdict"] == "UNAVAILABLE" and result["usage"]["total_tokens"] == 8
    assert result["validation_errors"] and "input" not in result["validation_errors"][0]
