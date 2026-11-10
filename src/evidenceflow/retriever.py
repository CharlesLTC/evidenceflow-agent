import math
import re
from collections import Counter


def tokenize(text):
    text = text.lower()
    # CJK bigrams keep compounds and avoid an external segmentation dictionary.
    words = re.findall(r"[a-z0-9]+", text)
    for span in re.findall(r"[\u4e00-\u9fff]+", text):
        words.extend(span[i : i + 2] for i in range(len(span) - 1))
        if len(span) == 1:
            words.append(span)
    return words


class Retriever:
    def __init__(self, store, encoder=None):
        self.store = store
        self.chunks = list(store.chunks.values())
        self.texts = [store.documents[c["doc_id"]]["title"] + " " + c["text"] for c in self.chunks]
        self.counts = [Counter(tokenize(t)) for t in self.texts]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avgdl = sum(self.lengths) / max(1, len(self.lengths))
        self.df = Counter(t for c in self.counts for t in c)
        self.encoder = encoder
        self.vectors = None

    def bm25(self, query):
        n = len(self.counts)
        scores = []
        for counts, length in zip(self.counts, self.lengths, strict=True):
            score = 0.0
            for token in set(tokenize(query)):
                freq = counts.get(token, 0)
                if freq:
                    idf = math.log(1 + (n - self.df[token] + 0.5) / (self.df[token] + 0.5))
                    score += idf * freq * 2.5 / (freq + 1.5 * (0.25 + 0.75 * length / self.avgdl))
            scores.append(score)
        return scores

    def dense(self, query):
        if self.encoder is None:
            raise RuntimeError("DENSE_UNAVAILABLE: configure a semantic embedding backend")
        import numpy as np

        if self.vectors is None:
            self.vectors = np.asarray(self.encoder.encode(self.texts), dtype=float)
            self.vectors /= np.maximum(np.linalg.norm(self.vectors, axis=1, keepdims=True), 1e-12)
        q = np.asarray(self.encoder.encode([query])[0], dtype=float)
        q /= max(float(np.linalg.norm(q)), 1e-12)
        return (self.vectors @ q).tolist()

    def search(self, query, top_k=5, strategy="bm25"):
        if strategy not in ("bm25", "dense", "hybrid"):
            return {
                "query": query,
                "strategy": strategy,
                "hits": [],
                "error": {"code": "INVALID_STRATEGY"},
            }
        if not isinstance(query, str) or not query.strip() or not 1 <= top_k <= 20:
            return {
                "query": query,
                "strategy": strategy,
                "hits": [],
                "error": {"code": "INVALID_SEARCH_ARGUMENTS"},
            }
        try:
            lexical = self.bm25(query)
            scores = lexical
            if strategy in ("dense", "hybrid"):
                semantic = self.dense(query)
                scores = semantic
                if strategy == "hybrid":
                    scores = [0.0] * len(lexical)
                    for values in (lexical, semantic):
                        for rank, idx in enumerate(
                            sorted(range(len(values)), key=lambda x: (-values[x], x)), 1
                        ):
                            if values[idx] > 0:
                                scores[idx] += 1 / (60 + rank)
            ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
            hits = []
            for i in ranked:
                if scores[i] <= 0:
                    continue
                c = self.chunks[i]
                d = self.store.documents[c["doc_id"]]
                hits.append(
                    {
                        "doc_id": d["doc_id"],
                        "chunk_id": c["chunk_id"],
                        "title": d["title"],
                        "topic": d["topic"],
                        "version_date": d["version_date"],
                        "score": float(scores[i]),
                        "preview": c["text"][:160],
                    }
                )
                if len(hits) >= top_k:
                    break
            return {"query": query, "strategy": strategy, "hits": hits}
        except Exception as exc:
            return {
                "query": query,
                "strategy": strategy,
                "hits": [],
                "error": {"code": "RETRIEVAL_UNAVAILABLE", "type": type(exc).__name__},
            }
