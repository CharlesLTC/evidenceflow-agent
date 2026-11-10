import hashlib
import json

from evidenceflow.config import ROOT
from scripts.evaluate_retrieval import metrics


def verify():
    report = json.loads((ROOT / "reports/retrieval_metrics.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "reports/retrieval_details.json").read_text(encoding="utf-8"))
    errors = []
    if report["answerable_queries"] < 30 or not 25 <= report["documents"] <= 40:
        errors.append("Insufficient corpus/gold samples")
    for name, data in report["strategies"].items():
        rows = [r for r in details if r["strategy"] == name]
        if data["status"] != "PASS":
            errors.append(name + ": " + data["status"])
            continue
        if len(rows) != report["queries"] or metrics(rows) != data["metrics"]:
            errors.append(name + ": metrics cannot be recomputed")
        if name.startswith("D_") and not all(
            r["model_calls"] > 0 and r["trace"] and (ROOT / r["trace"]).exists() for r in rows
        ):
            errors.append("D has no real model traces")
    for f, digest in report["dataset_sha256"].items():
        if hashlib.sha256((ROOT / "data" / f).read_bytes()).hexdigest() != digest:
            errors.append("Dataset changed after experiment: " + f)
    for f in ("recall_at_3.png", "quality_cost.png"):
        if not (ROOT / "reports/charts" / f).exists():
            errors.append("Missing chart: " + f)
    result = {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "same_gold_ids": len({r["id"] for r in details}),
        "raw_rows": len(details),
    }
    print(json.dumps(result, indent=2))
    return not errors


if __name__ == "__main__":
    raise SystemExit(0 if verify() else 1)
