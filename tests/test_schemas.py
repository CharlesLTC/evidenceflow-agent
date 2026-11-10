import pytest
from pydantic import ValidationError

from evidenceflow.config import Settings
from evidenceflow.schemas import AskRequest, Document


@pytest.mark.parametrize("question", ["", " ", "\n"])
def test_empty_question_rejected(question):
    with pytest.raises(ValidationError):
        AskRequest(question=question)


@pytest.mark.parametrize("kwargs", [{"max_model_steps": 9}, {"max_tool_calls": 13},
                                  {"session_id": "../escape"}, {"mode": "invented"}])
def test_invalid_request_rejected(kwargs):
    with pytest.raises(ValidationError):
        AskRequest(question="Q", **kwargs)


def test_data_contract():
    import json
    from evidenceflow.config import ROOT
    docs = [Document.model_validate(d) for d in json.loads((ROOT / "data/documents.json").read_text(encoding="utf-8"))]
    assert len(docs) == 8
    assert len({d.doc_id for d in docs}) == len(docs)
    assert docs[0].scope is None and docs[1].scope is None


def test_live_credentials_are_required():
    assert "LLM_API_KEY" in Settings().live_blocker()

