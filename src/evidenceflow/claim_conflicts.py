"""Conservative numeric policy claims, compared only within the same topic/field/unit."""

import re
from itertools import combinations


def extract_claims(doc):
    claims = []
    for sentence in re.split(r"(?<=[。；\n])", doc["content"]):
        # This deliberately handles bounded synthetic policy fields, not arbitrary entailment.
        for match in re.finditer(r"(\d+)\s*(个工作日|工作日|天|元|小时|个月)", sentence):
            before = sentence[: match.start()]
            field = (
                "提交期限"
                if any(w in before for w in ("报销", "提交"))
                else "审批时长"
                if any(w in before for w in ("审批", "申领"))
                else "完成期限"
                if "完成" in sentence
                else doc["topic"]
            )
            claims.append(
                {
                    "topic": doc["topic"],
                    "field": field,
                    "value": match.group(1),
                    "unit": match.group(2),
                    "scope": doc["scope"],
                    "doc_id": doc["doc_id"],
                    "quote": sentence.strip(),
                }
            )
    return claims


def detect_conflicts(documents):
    claims = [c for d in documents for c in extract_claims(d)]
    conflicts = []
    seen = set()
    for a, b in combinations(claims, 2):
        if a["doc_id"] == b["doc_id"]:
            continue
        if (a["topic"], a["field"], a["unit"]) != (b["topic"], b["field"], b["unit"]):
            continue
        # Different explicit, disjoint scopes are legitimate policy differences.
        if a["scope"] and b["scope"] and a["scope"] != b["scope"]:
            if "全体员工" not in (a["scope"], b["scope"]):
                continue
        if a["value"] == b["value"]:
            continue
        pair = tuple(sorted((a["doc_id"], b["doc_id"]))) + (a["field"],)
        if pair in seen:
            continue
        seen.add(pair)
        conflicts.append(
            {
                "topic": a["topic"],
                "field": a["field"],
                "documents": [a["doc_id"], b["doc_id"]],
                "values": [a["value"] + a["unit"], b["value"] + b["unit"]],
                "resolution": "UNRESOLVED",
                "scope": [a["scope"], b["scope"]],
            }
        )
    return conflicts
