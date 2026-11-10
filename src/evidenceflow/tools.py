from pydantic import Field

from evidenceflow.schemas import AnswerSubmission, StrictModel


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
    "submit_answer": AnswerSubmission,
}
TOOL_DESCRIPTIONS = {
    "search_documents": "Search untrusted previews; call read_document before citing. Ranking scores do not prove answerability. Supports bm25/dense/hybrid; use configured preferred strategy first, bm25 remains available after retrieval errors.",
    "read_document": "Read exact original chunks with version, scope and offsets. Only these quotes can be cited.",
    "inspect_versions": "Inspect all known topic versions and scopes. Newer does not imply higher precedence.",
    "submit_answer": "Submit status, citations and missing_info. Prefer omitting answer: the server renders exact quote lines and the correct status suffix. This avoids formatting retries; every citation, conflict and fact still passes the unchanged strict Evidence Guard.",
}


def tool_schemas(default_strategy="bm25"):
    schemas = [
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
    search = schemas[0]["function"]
    search["parameters"]["properties"]["strategy"]["default"] = default_strategy
    search["parameters"]["properties"]["strategy"]["enum"] = ["bm25", "dense", "hybrid"]
    search["description"] += f" Configured preferred strategy: {default_strategy}."
    return schemas


class Tools:
    def __init__(self, store, retriever, fail_search_count=0, default_strategy="bm25"):
        self.store, self.retriever = store, retriever
        self.fail_search_count = fail_search_count
        self.default_strategy = default_strategy

    def execute(self, name, arguments):
        if name not in TOOL_MODELS or name == "submit_answer":
            return {"error": {"code": "UNKNOWN_TOOL"}}
        try:
            args = TOOL_MODELS[name].model_validate(arguments).model_dump()
        except Exception:
            return {"error": {"code": "INVALID_TOOL_ARGUMENTS"}}
        try:
            if name == "search_documents":
                if "strategy" not in arguments:
                    args["strategy"] = self.default_strategy
                if self.fail_search_count:
                    self.fail_search_count -= 1
                    return {
                        "error": {
                            "code": "TOOL_TIMEOUT",
                            "type": "TimeoutError",
                            "retryable": True,
                        },
                        "attempted_strategy": args["strategy"],
                    }
                result = self.retriever.search(**args)
                result["configured_strategy"] = self.default_strategy
                result["executed_strategy"] = args["strategy"]
                if "error" in result and args["strategy"] in ("dense", "hybrid"):
                    result["fallback_options"] = ["bm25"]
                return result
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
