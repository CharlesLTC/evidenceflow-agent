import re

from evidenceflow.claim_conflicts import detect_conflicts

INSTRUCTION_TEXT = re.compile(
    r"忽略.{0,12}(?:指令|规则)|调用\s*shell|输出无引用|ignore.{0,30}(?:instructions|rules)",
    re.IGNORECASE,
)

SUFFIXES = {
    "COMPLETED": "",
    "NEEDS_CLARIFICATION": "适用范围及优先级尚待确认，当前无法确定唯一规则。",
    "INSUFFICIENT_EVIDENCE": "当前资料不足，无法依据知识库回答。",
    "FAILED": "工具或模型服务不可用，本次未能完成核验。",
    "INCOMPLETE": "执行预算已用尽，本次核验未完成。",
}


def render_answer(status, citations):
    parts = [f"{c.doc_id}：{c.quote}" for c in citations]
    if SUFFIXES[status]:
        parts.append(SUFFIXES[status])
    return "\n".join(parts)


class EvidenceGuard:
    def __init__(self, store):
        self.store = store

    def validate(self, draft, loaded, discovered, observations=None):
        errors = []
        for c in draft.citations:
            if INSTRUCTION_TEXT.search(c.quote):
                errors.append(
                    "INSTRUCTION_TEXT_NOT_POLICY_EVIDENCE: quote only the actual policy sentence"
                )
            d = self.store.documents.get(c.doc_id)
            chunk = self.store.chunks.get(c.chunk_id)
            if not d:
                errors.append("UNKNOWN_DOCUMENT:" + c.doc_id)
                continue
            if c.chunk_id not in loaded:
                errors.append("NOT_READ:" + c.chunk_id)
            if not chunk or chunk["doc_id"] != c.doc_id:
                errors.append("INVALID_CHUNK:" + c.chunk_id)
            elif c.quote not in chunk["text"]:
                errors.append("QUOTE_NOT_EXACT:" + c.chunk_id)
            if c.version_date != d["version_date"]:
                errors.append("VERSION_MISMATCH:" + c.doc_id)
        topics = {
            self.store.documents[c.doc_id]["topic"]
            for c in draft.citations
            if c.doc_id in self.store.documents
        }
        # Only observed candidate documents participate: no secret automatic document reads.
        candidates = [
            self.store.documents[d]
            for d in discovered
            if d in self.store.documents and self.store.documents[d]["topic"] in topics
        ]
        conflicts = detect_conflicts(candidates)
        if conflicts:
            if draft.status != "NEEDS_CLARIFICATION":
                errors.append("UNRESOLVED_CONFLICT")
            required = {d for c in conflicts for d in c["documents"]}
            if not required <= {c.doc_id for c in draft.citations}:
                errors.append("CONFLICT_REFERENCES_MISSING")
        if draft.status == "COMPLETED" and not draft.citations:
            errors.append("EVIDENCE_REQUIRED")
        if (
            draft.status in ("NEEDS_CLARIFICATION", "INSUFFICIENT_EVIDENCE", "FAILED", "INCOMPLETE")
            and not draft.missing_info
        ):
            errors.append("MISSING_INFO_REQUIRED")
        if draft.status == "INSUFFICIENT_EVIDENCE" and draft.citations:
            errors.append("ABSTENTION_MUST_NOT_CITE_IRRELEVANT_DOCUMENTS")
        if draft.status == "INSUFFICIENT_EVIDENCE" and observations:
            failures = any("error" in o for o in observations)
            succeeded = any(
                "error" not in o and any(k in o for k in ("hits", "chunks", "versions"))
                for o in observations
            )
            if failures and not succeeded:
                errors.append("TOOL_FAILURE_IS_NOT_KNOWLEDGE_ABSENCE: use FAILED or INCOMPLETE")
        for fact in draft.facts:
            if (
                fact.citation_index >= len(draft.citations)
                or fact.text not in draft.citations[fact.citation_index].quote
            ):
                errors.append("UNSUPPORTED_FACT")
        # Extractive output closes the gap where a valid quote accompanies an invented assertion.
        # No statistical/LLM self-reported entailment score is treated as a proof.
        expected = render_answer(draft.status, draft.citations)
        if draft.answer.strip() != expected:
            errors.append(
                "ANSWER_NOT_EXTRACTIVE: use exact Dxx：quote lines and the prescribed status suffix"
            )
        return {
            "valid": not errors,
            "errors": errors,
            "conflicts": conflicts,
            "expected_answer_format": expected if errors else None,
        }
