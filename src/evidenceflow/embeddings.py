"""Real quantized multilingual transformer embeddings; no lexical surrogate fallback."""

import json
import os
import threading
from pathlib import Path

import numpy as np

from evidenceflow.config import ROOT

MODEL = "Xenova/paraphrase-multilingual-MiniLM-L12-v2"


class OnnxEncoder:
    def __init__(self, directory=None):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.directory = Path(directory or ROOT / ".cache/embeddings")
        manifest = self.directory / "manifest.json"
        if not manifest.exists():
            raise RuntimeError(
                "EMBEDDINGS_NOT_DOWNLOADED: run python -m scripts.download_embeddings"
            )
        self.metadata = json.loads(manifest.read_text(encoding="utf-8"))
        self.tokenizer = Tokenizer.from_file(str(self.directory / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=128)
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(self.directory / "model_quantized.onnx"),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )
        self.lock = threading.RLock()
        self.memo = {}

    def encode(self, texts):
        with self.lock:
            missing = list(dict.fromkeys(t for t in texts if t not in self.memo))
            for start in range(0, len(missing), 16):
                batch = missing[start : start + 16]
                tokens = self.tokenizer.encode_batch(batch)
                feeds = {
                    "input_ids": np.asarray([t.ids for t in tokens], dtype=np.int64),
                    "attention_mask": np.asarray(
                        [t.attention_mask for t in tokens], dtype=np.int64
                    ),
                    "token_type_ids": np.asarray([t.type_ids for t in tokens], dtype=np.int64),
                }
                outputs = self.session.run(
                    None, {v.name: feeds[v.name] for v in self.session.get_inputs()}
                )
                embeddings = outputs[0]
                if embeddings.ndim == 3:
                    mask = feeds["attention_mask"][:, :, None]
                    embeddings = (embeddings * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
                embeddings = embeddings / np.maximum(
                    np.linalg.norm(embeddings, axis=1, keepdims=True), 1e-12
                )
                self.memo.update(zip(batch, embeddings.tolist(), strict=True))
            return [self.memo[t] for t in texts]


def configured_encoder(root=ROOT):
    if os.getenv("EMBEDDING_BACKEND", "onnx") != "onnx":
        raise RuntimeError("Only the documented ONNX backend is configured in this build")
    return OnnxEncoder(root / ".cache/embeddings")
