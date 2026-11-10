from evidenceflow.schemas import AskRequest


def test_followup_uses_same_session_and_survives_new_service(service_factory):
    first = service_factory()
    result = first.ask(AskRequest(question="电脑怎么申领？", session_id="followup", mode="mock"))
    second = service_factory()
    answer = second.ask(AskRequest(question="那多久批下来？", session_id="followup", mode="mock"))
    assert result.status == answer.status == "COMPLETED"
    assert "3个工作日" in answer.answer
    assert len(second.sessions.history("followup", "mock")) == 2


def test_sessions_and_modes_are_isolated(service_factory):
    s = service_factory()
    s.ask(AskRequest(question="电脑怎么申领？", session_id="one", mode="mock"))
    assert s.sessions.history("two") == []
    assert s.sessions.history("one", "live") == []

