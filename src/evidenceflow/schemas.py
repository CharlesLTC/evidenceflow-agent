from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Status = Literal[
    "COMPLETED", "NEEDS_CLARIFICATION", "INSUFFICIENT_EVIDENCE", "FAILED", "INCOMPLETE"
]
Mode = Literal["live", "mock", "fake_model"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Document(StrictModel):
    doc_id: str = Field(pattern=r"^D\d{2,}$")
    title: str
    version_date: str
    effective_date: str | None
    scope: str | None
    status: str
    topic: str
    content: str = Field(min_length=1)


class Citation(StrictModel):
    doc_id: str
    version_date: str
    quote: str = Field(min_length=4)
    chunk_id: str


class Fact(StrictModel):
    """A claim is extractive: exact evidence plus a citation index, never model self-scoring."""

    text: str
    citation_index: int = Field(ge=0)


class Draft(StrictModel):
    answer: str = Field(min_length=1, max_length=8000)
    status: Status
    citations: list[Citation] = Field(default_factory=list, max_length=20)
    facts: list[Fact] = Field(default_factory=list, max_length=30)
    missing_info: list[str] = Field(default_factory=list, max_length=20)


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    mode: Mode = "live"
    max_model_steps: int = Field(default=8, ge=1, le=8)
    max_tool_calls: int = Field(default=12, ge=1, le=12)
    fail_search_count: int = Field(default=0, ge=0, le=12)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("question must contain non-whitespace characters")
        return value.strip()


class Answer(StrictModel):
    question: str
    answer: str
    status: Status
    citations: list[Citation] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    conflicts: list[dict] = Field(default_factory=list)
    steps_used: int = 0
    tool_calls_used: int = 0
    trace_id: str
    session_id: str
    mode: Mode
    model_name: str
    latency_ms: float = 0
    usage: dict = Field(default_factory=dict)
    error_code: str | None = None
