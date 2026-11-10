from pydantic import Field

from evidenceflow.schemas import Draft, StrictModel


class SearchArgs(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    strategy: str = "bm25"


class ReadArgs(StrictModel):
    doc_id: str
    chunk_ids: list[str] | None = None


class VersionsArgs(StrictModel):
    topic: str = Field(min_length=1)


TOOL_MODELS = {
    "search_documents": SearchArgs,
    "read_document": ReadArgs,
    "inspect_versions": VersionsArgs,
    "submit_answer": Draft,
}
TOOL_DESCRIPTIONS = {
    "search_documents": "Search untrusted previews; call read_document before citing. Supports bm25/dense/hybrid.",
    "read_document": "Read exact original chunks with version, scope and offsets. Only these quotes can be cited.",
    "inspect_versions": "Inspect all known topic versions and scopes. Newer does not imply higher precedence.",
    "submit_answer": "Propose a final extractive answer. Evidence Guard can reject and return errors for revision.",
}


def tool_schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": TOOL_DESCRIPTIONS[name],
                "parameters": model.model_json_schema(),
            },
        }
        for name, model in TOOL_MODELS.items()
    ]


class Tools:
    def __init__(self, store, retriever, fail_search_count=0):
        self.store, self.retriever = store, retriever
        self.fail_search_count = fail_search_count

    def execute(self, name, arguments):
        if name not in TOOL_MODELS or name == "submit_answer":
            return {"error": {"code": "UNKNOWN_TOOL"}}
        try:
            args = TOOL_MODELS[name].model_validate(arguments).model_dump()
        except Exception:
            return {"error": {"code": "INVALID_TOOL_ARGUMENTS"}}
        try:
            if name == "search_documents":
                if self.fail_search_count:
                    self.fail_search_count -= 1
                    raise TimeoutError("injected synthetic search timeout")
                return self.retriever.search(**args)
            if name == "read_document":
                return self.store.read(**args)
            return self.store.versions(**args)
        except Exception as exc:
            return {
                "error": {
                    "code": "TOOL_TIMEOUT" if isinstance(exc, TimeoutError) else "TOOL_FAILURE",
                    "type": type(exc).__name__,
                    "retryable": True,
                }
            }
