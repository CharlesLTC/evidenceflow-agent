import pytest

from scripts.evaluate_retrieval import metrics


def test_macro_recall_mrr_and_unanswerable_denominator():
    rows = [
        {
            "expected_doc_ids": ["D01", "D02"],
            "ranked_doc_ids": ["D03", "D02"],
            "latency_ms": 1,
            "model_calls": 0,
            "tool_calls": 1,
        },
        {
            "expected_doc_ids": ["D03"],
            "ranked_doc_ids": ["D03"],
            "latency_ms": 2,
            "model_calls": 0,
            "tool_calls": 1,
        },
        {
            "expected_doc_ids": [],
            "ranked_doc_ids": ["D01"],
            "latency_ms": 3,
            "model_calls": 0,
            "tool_calls": 1,
        },
    ]
    m = metrics(rows)
    assert m["answerable_count"] == 2
    assert m["recall_at_3"]["value"] == pytest.approx(0.75)
    assert m["recall_at_3"]["relevant_retrieved"] == 2
    assert m["recall_at_3"]["relevant_total"] == 3
    assert m["mrr_at_5"]["value"] == pytest.approx(0.75)
    assert m["correct_abstention_rate"] is None
