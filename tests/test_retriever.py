import json

import pytest

from evidenceflow.config import ROOT
from evidenceflow.document_store import DocumentStore
from evidenceflow.retriever import Retriever
from evidenceflow.tools import Tools


@pytest.fixture
def store():
    return DocumentStore(ROOT / "data/documents.json")


@pytest.mark.parametrize(
    "query,expected",
    [
        ("办公电脑申领审批需要多久？", {"D03"}),
        ("差旅报销期限是多久？", {"D01", "D02"}),
        ("领电脑一般几天能批下来？", {"D03"}),
    ],
)
def test_search_and_read(store, query, expected):
    hits = Retriever(store).search(query)["hits"]
    assert expected <= {h["doc_id"] for h in hits[:3]}
    for doc_id in expected:
        read = store.read(doc_id)
        for c in read["chunks"]:
            assert read["content"][c["start"] : c["end"]] == c["text"]


def test_empty_invalid_and_dense_unavailable(store):
    r = Retriever(store)
    assert r.search("火星殖民火箭")["hits"] == []
    assert r.search("")["error"]["code"] == "INVALID_SEARCH_ARGUMENTS"
    assert r.search("电脑", strategy="dense")["error"]["code"] == "RETRIEVAL_UNAVAILABLE"
    assert store.read("D999")["error"]["code"] == "DOCUMENT_NOT_FOUND"
    assert store.read("D03", ["D01-C01"])["error"]["code"] == "CHUNK_NOT_FOUND"


def test_scope_priority_remains_unknown(store):
    versions = store.versions("差旅报销")
    assert {v["doc_id"] for v in versions["versions"]} == {"D01", "D02"}
    assert versions["precedence"] is None
    assert all(v["scope"] is None for v in versions["versions"])


def test_fault_is_real_observation(store):
    t = Tools(store, Retriever(store), fail_search_count=1)
    assert t.execute("search_documents", {"query": "电脑"})["error"]["code"] == "TOOL_TIMEOUT"
    assert t.execute("search_documents", {"query": "电脑"})["hits"]
    assert t.execute("read_document", {"unknown": 1})["error"]["code"] == "INVALID_TOOL_ARGUMENTS"


def test_duplicate_loader_rejected(tmp_path, store):
    p = tmp_path / "duplicate.json"
    doc = store.documents["D03"]
    p.write_text(json.dumps([doc, doc]), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        DocumentStore(p)


def test_long_document_spans_are_exact(tmp_path, store):
    doc = store.documents["D03"] | {"content": "甲乙丙。" * 300}
    p = tmp_path / "long.json"
    p.write_text(json.dumps([doc]), encoding="utf-8")
    read = DocumentStore(p).read("D03")
    assert "".join(c["text"] for c in read["chunks"]) == doc["content"]
