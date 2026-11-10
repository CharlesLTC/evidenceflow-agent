from evidenceflow.claim_conflicts import detect_conflicts, extract_claims
from evidenceflow.config import ROOT
from evidenceflow.document_store import DocumentStore


def docs():
    s = DocumentStore(ROOT / "data/documents.json")
    return [s.documents["D01"], s.documents["D02"]]


def test_unscoped_versions_conflict_and_dates_do_not_resolve():
    conflicts = detect_conflicts(docs())
    assert len(conflicts) == 1
    assert conflicts[0]["values"] == ["30天", "15天"]
    assert conflicts[0]["resolution"] == "UNRESOLVED"


def test_disjoint_scopes_are_not_conflicts():
    a, b = docs()
    a["scope"], b["scope"] = "正式员工", "实习生"
    assert detect_conflicts([a, b]) == []


def test_unknown_and_all_employee_scopes_may_overlap():
    a, b = docs()
    a["scope"], b["scope"] = "全体员工", "实习生"
    assert detect_conflicts([a, b])


def test_equal_values_not_conflicts():
    a, b = docs()
    b["content"] = b["content"].replace("15", "30")
    assert not detect_conflicts([a, b])


def test_claims_preserve_quote_and_unit():
    claim = extract_claims(docs()[0])[0]
    assert claim["quote"] in docs()[0]["content"]
    assert claim["value"] == "30" and claim["unit"] == "天"
