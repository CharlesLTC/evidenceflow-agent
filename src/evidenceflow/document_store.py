import json
from datetime import date
from pathlib import Path

from evidenceflow.schemas import Document


class DocumentStore:
    def __init__(self, path: Path):
        self.path = path
        docs = [Document.model_validate(d) for d in json.loads(path.read_text(encoding="utf-8"))]
        if len({d.doc_id for d in docs}) != len(docs):
            raise ValueError("duplicate doc_id")
        self.documents = {d.doc_id: d.model_dump() for d in docs}
        self.chunks = {}
        for doc in docs:
            date.fromisoformat(doc.version_date)
            if doc.effective_date:
                date.fromisoformat(doc.effective_date)
            # Exact contiguous spans, including punctuation and whitespace.
            for i, start in enumerate(range(0, len(doc.content), 500), 1):
                end = min(start + 500, len(doc.content))
                cid = f"{doc.doc_id}-C{i:02}"
                self.chunks[cid] = dict(doc_id=doc.doc_id, chunk_id=cid, start=start,
                                        end=end, text=doc.content[start:end])

    def read(self, doc_id, chunk_ids=None):
        if doc_id not in self.documents:
            return {"error": {"code": "DOCUMENT_NOT_FOUND", "doc_id": doc_id}}
        chunks = [c for c in self.chunks.values() if c["doc_id"] == doc_id]
        if chunk_ids is not None:
            if not chunk_ids or any(c not in {x["chunk_id"] for x in chunks} for c in chunk_ids):
                return {"error": {"code": "CHUNK_NOT_FOUND", "doc_id": doc_id}}
            chunks = [c for c in chunks if c["chunk_id"] in chunk_ids]
        return {**self.documents[doc_id], "chunks": chunks, "trust": "untrusted_document_data"}

    def versions(self, topic):
        versions = [{k: d[k] for k in ("doc_id", "title", "topic", "version_date", "scope", "effective_date", "status")}
                    for d in self.documents.values() if topic in d["topic"] or d["topic"] in topic]
        return {"topic": topic, "versions": versions, "precedence": None,
                "note": "Newer version alone does not establish precedence."}

