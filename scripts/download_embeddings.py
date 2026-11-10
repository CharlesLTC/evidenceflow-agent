"""Download fixed-revision public model artifacts to the ignored local cache."""

import hashlib
import json

import httpx

from evidenceflow.config import ROOT
from evidenceflow.embeddings import MODEL
from evidenceflow.trace_writer import utc_now, write_json


def main():
    directory = ROOT / ".cache/embeddings"
    directory.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        info = client.get(f"https://huggingface.co/api/models/{MODEL}")
        info.raise_for_status()
        revision = info.json()["sha"]
        files = {}
        for source, target in [
            ("tokenizer.json", "tokenizer.json"),
            ("onnx/model_quantized.onnx", "model_quantized.onnx"),
        ]:
            dest = directory / target
            digest = hashlib.sha256()
            with client.stream(
                "GET", f"https://huggingface.co/{MODEL}/resolve/{revision}/{source}"
            ) as response:
                response.raise_for_status()
                with dest.open("wb") as f:
                    for data in response.iter_bytes(1024 * 1024):
                        f.write(data)
                        digest.update(data)
            files[target] = {"sha256": digest.hexdigest(), "bytes": dest.stat().st_size}
            print(f"Downloaded {target}: {dest.stat().st_size} bytes", flush=True)
    manifest = {
        "model": MODEL,
        "revision": revision,
        "timestamp": utc_now(),
        "pooling": "attention_mask_mean_then_L2",
        "max_tokens": 128,
        "files": files,
    }
    write_json(directory / "manifest.json", manifest)
    write_json(ROOT / "reports/embedding_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
