import json
import subprocess

from evidenceflow.config import ROOT
from evidenceflow.schemas import Answer
from evidenceflow.trace_writer import write_json
from scripts.security_scan import EXCLUDED, scan
from scripts.validate_live_evidence import validate

REQUIRED = [
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    ".env.example",
    "CODEX_WORKLOG.md",
    "data/documents.json",
    "data/eval_questions.jsonl",
    "data/gold_labels.json",
    "docs/01-requirements.md",
    "docs/02-solution.md",
    "docs/03-evaluation.md",
    "docs/04-ai-usage.md",
    "docs/05-retrospective.md",
    "docs/06-architecture.md",
    "docs/07-test-plan.md",
    "docs/08-experiments.md",
    "docs/09-time-log.md",
    "reports/retrieval_metrics.json",
    "reports/acceptance_results.live.json",
    "reports/final_acceptance.md",
    "reports/ui_smoke.json",
]


def verify():
    errors = []
    for name in REQUIRED:
        if not (ROOT / name).is_file() or not (ROOT / name).stat().st_size:
            errors.append("Missing/empty: " + name)
    json_count = 0
    for path in ROOT.rglob("*.json"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED or part.endswith(".egg-info") for part in relative.parts):
            continue
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
            json_count += 1
        except (ValueError, OSError):
            errors.append("Invalid JSON: " + relative.as_posix())
    triplets = 0
    for mode in ("live", "mock", "fake_model"):
        for path in (ROOT / f"examples/traces/{mode}").glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = Answer.model_validate(payload["result"])
            if result.mode != mode or payload["mode"] != mode:
                errors.append("Mode/directory mismatch: " + str(path.name))
            output = ROOT / f"examples/outputs/{mode}/{result.trace_id}.json"
            inp = ROOT / f"examples/inputs/{mode}-{result.trace_id}.json"
            if not output.exists() or not inp.exists():
                errors.append("Incomplete triplet: " + result.trace_id)
            else:
                triplets += 1
            # Verify each quote against the actual read Observation, including mutated corpora.
            read_chunks = {
                c["chunk_id"]: (
                    c["text"],
                    e["observation"]["version_date"],
                    e["observation"]["doc_id"],
                )
                for e in payload["events"]
                if e["kind"] == "tool_observation"
                and e["tool_name"] == "read_document"
                and "chunks" in e["observation"]
                for c in e["observation"]["chunks"]
            }
            for citation in result.citations:
                evidence = read_chunks.get(citation.chunk_id)
                if (
                    not evidence
                    or citation.quote not in evidence[0]
                    or citation.version_date != evidence[1]
                    or citation.doc_id != evidence[2]
                ):
                    errors.append("Invalid persisted quote: " + result.trace_id)
    if triplets < 3:
        errors.append("At least three actual triplets required")
    for i in range(7):
        path = ROOT / f"reports/gates/P{i}.json"
        if not path.exists() or json.loads(path.read_text(encoding="utf-8"))["status"] != "PASS":
            errors.append(f"P{i} has not passed")
    security = scan(ROOT)
    if security["findings"]:
        errors.append("Secret scan failed (values suppressed)")
    tracked = (
        subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
        .stdout.decode("utf-8")
        .split("\0")
    )
    for name in tracked:
        if name and (
            name == ".env"
            or name.startswith(".env.")
            and name != ".env.example"
            or any(part in EXCLUDED for part in name.split("/"))
        ):
            errors.append("Forbidden tracked file: " + name)
    live = validate()
    errors.extend(live["errors"])
    report = {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        "json_files_checked": json_count,
        "actual_triplets": triplets,
        "security": security,
        "live_six": live["six_passed"],
        "scope": "Local artifact validation; GitHub publication verified separately",
    }
    write_json(ROOT / "reports/artifact_verification.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return not errors


if __name__ == "__main__":
    raise SystemExit(0 if verify() else 1)
