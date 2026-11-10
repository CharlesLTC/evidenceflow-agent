import argparse
import json

from evidenceflow.config import ROOT

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=[f"P{i}" for i in range(9)])
    args = parser.parse_args()
    path = ROOT / f"reports/gates/{args.stage}.json"
    if not path.exists():
        print(json.dumps({"stage": args.stage, "status": "MISSING"}))
        raise SystemExit(1)
    gate = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    raise SystemExit(0 if gate["status"] in ("PASS", "SKIPPED_OPTIONAL") else 1)
