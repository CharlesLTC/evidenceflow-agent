"""Scan deliverable text without printing matched secret values."""
import json
import re
from pathlib import Path

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import SECRET_PATTERN, write_json

EXCLUDED = {".git", ".venv", ".cache", ".tools", "__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
ASSIGNMENT = re.compile(r"(?im)^[ \t]*(?:LLM_API_KEY|OPENAI_API_KEY|EMBEDDING_API_KEY|GH_TOKEN|GITHUB_TOKEN)[ \t]*=[ \t]*[^\s#\"']{8,}")


def scan(root):
    findings = []
    scanned = 0
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if not p.is_file() or any(part in EXCLUDED or part.endswith(".egg-info") for part in rel.parts):
            continue
        if p.name.startswith(".env") and p.name != ".env.example":
            continue  # Local credentials deliberately excluded from the delivery set.
        try:
            content = p.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        scanned += 1
        for pattern in (SECRET_PATTERN, ASSIGNMENT):
            for match in pattern.finditer(content):
                findings.append({"path": rel.as_posix(), "line": content[:match.start()].count("\n") + 1,
                                 "type": "credential_pattern"})
    return {"status": "FAIL" if findings else "PASS", "scanned_text_files": scanned,
            "findings": findings, "scope": "deliverable files, excluding ignored environments/cache and local .env"}


if __name__ == "__main__":
    result = scan(ROOT)
    write_json(ROOT / "reports/security_scan.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result["findings"] else 0)
