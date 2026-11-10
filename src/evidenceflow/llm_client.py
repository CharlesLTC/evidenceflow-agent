"""OpenAI-compatible HTTP tool calling, with no automatic model or tool retries."""
import json
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from evidenceflow.claim_conflicts import detect_conflicts
from evidenceflow.evidence_guard import render_answer
from evidenceflow.schemas import Citation


@dataclass
class Decision:
    tool_calls: list[dict]
    usage: dict = field(default_factory=dict)


class Model(Protocol):
    name: str
    mode: str

    def decide(self, messages: list[dict], tools: list[dict]) -> Decision: ...


class ModelError(RuntimeError):
    pass


class LiveModel:
    mode = "live"

    def __init__(self, settings, transport=None):
        self.name = settings.model_name
        self.settings = settings
        self.transport = transport

    def decide(self, messages, tools):
        blocker = self.settings.live_blocker()
        if blocker:
            raise ModelError("BLOCKED_LIVE")
        with httpx.Client(timeout=self.settings.timeout, transport=self.transport) as client:
            response = client.post(self.settings.base_url.rstrip("/") + "/chat/completions",
                                   headers={"Authorization": "Bearer " + self.settings.api_key},
                                   json={"model": self.name, "messages": messages, "tools": tools,
                                         "tool_choice": "required", "temperature": 0})
            if response.status_code != 200:
                # Raw response/exception text may contain credentials or a private echo. Do not log it.
                raise ModelError("MODEL_HTTP_" + str(response.status_code))
            payload = response.json()
        try:
            calls = payload["choices"][0]["message"].get("tool_calls", [])
            clean = []
            for call in calls:
                args = call["function"]["arguments"]
                clean.append({"id": call["id"], "name": call["function"]["name"],
                              "arguments": json.loads(args) if isinstance(args, str) else args})
            return Decision(clean, payload.get("usage") or {})
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelError("INVALID_MODEL_TOOL_RESPONSE") from exc


class ScriptedModel:
    """Deterministic test double only. Never available as a live fallback."""
    mode = "fake_model"
    name = "scripted-test-double"

    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.seen = []

    def decide(self, messages, tools):
        self.seen.append(json.loads(json.dumps(messages)))
        item = next(self.decisions)
        return item(messages) if callable(item) else item


def call(name, **arguments):
    import uuid
    return Decision([{"id": "call_" + uuid.uuid4().hex[:10], "name": name, "arguments": arguments}])


class MockModel:
    """Explicit offline simulator. Heuristics demonstrate plumbing, not LLM autonomy."""
    mode = "mock"
    name = "offline-observation-simulator"

    def decide(self, messages, tools):
        observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        actions = [c for m in messages if m["role"] == "assistant" for c in m.get("tool_calls", [])]
        questions = [m["content"] for m in messages if m["role"] == "user"]
        query = " ".join(questions[-3:])
        reads = [o for o in observations if "chunks" in o and "error" not in o]
        searches = [o for o in observations if "hits" in o]
        errors = [o for o in observations if "error" in o]
        if not observations:
            return call("search_documents", query=query, top_k=5, strategy="bm25")
        if errors and len(errors) >= 2 and not reads:
            return self.submit("FAILED", [], ["检索工具连续失败"])
        if observations[-1].get("error"):
            return call("search_documents", query=query + " 制度", top_k=8, strategy="bm25")
        if searches:
            hits = searches[-1]["hits"]
            if not hits:
                return self.submit("INSUFFICIENT_EVIDENCE", [], ["知识库未包含该问题的依据"])
            # Topic coherence is solely for the simulator. The live graph has no question branches.
            top_topic = hits[0]["topic"]
            wanted = [h["doc_id"] for h in hits if h["topic"] == top_topic]
            loaded_ids = {d["doc_id"] for d in reads}
            for doc_id in wanted:
                if doc_id not in loaded_ids:
                    return call("read_document", doc_id=doc_id)
        if reads:
            conflicts = detect_conflicts(reads)
            if conflicts and not any("versions" in o for o in observations):
                return call("inspect_versions", topic=reads[0]["topic"])
            citations = [Citation(doc_id=d["doc_id"], version_date=d["version_date"],
                                  quote=d["chunks"][0]["text"].split("。")[0] + "。",
                                  chunk_id=d["chunks"][0]["chunk_id"]) for d in reads]
            return self.submit("NEEDS_CLARIFICATION" if conflicts else "COMPLETED", citations,
                               ["两份制度的适用范围及优先级"] if conflicts else [])
        return self.submit("FAILED", [], ["离线模拟器未能选择有效动作"])

    @staticmethod
    def submit(status, citations, missing_info):
        return call("submit_answer", answer=render_answer(status, citations), status=status,
                    citations=[c.model_dump() for c in citations], missing_info=missing_info)

