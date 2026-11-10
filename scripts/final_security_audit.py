"""Audit deliverable files and reachable Git objects; report metadata, never matched values."""

import argparse
import hashlib
import io
import json
import os
import re
import subprocess

from dotenv import dotenv_values

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import SECRET_PATTERN, utc_now, write_json
from scripts.final_acceptance import EXCLUDED
from scripts.security_scan import ASSIGNMENT, scan

PRIVATE_PATH = re.compile(r"\bS-1-5-21-\d+(?:-\d+){2,}\b|(?i:[a-z]:[\\/]+Users[\\/]+[^\\/\s\"']+)")
PRIVATE_KEY = re.compile(r"-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----")


def git(*args, payload=None):
    return subprocess.check_output(["git", *args], cwd=ROOT, input=payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="FINAL_ACCEPTANCE/F7_security_audit.json")
    args = parser.parse_args()
    configured = dict(dotenv_values(ROOT / ".env")) | dict(os.environ)
    keys = [
        value.encode()
        for name, value in configured.items()
        if name
        in {"LLM_API_KEY", "OPENAI_API_KEY", "EMBEDDING_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"}
        and isinstance(value, str)
        and len(value) >= 8
    ]

    def inspect(raw):
        found = []
        if any(key in raw for key in keys):
            found.append("configured_credential_value")
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            return found
        for kind, pattern in (
            ("credential_pattern", SECRET_PATTERN),
            ("credential_assignment", ASSIGNMENT),
            ("private_key", PRIVATE_KEY),
            ("private_local_path", PRIVATE_PATH),
        ):
            if pattern.search(text):
                found.append(kind)
        return found

    tracked = git("ls-files", "-z").decode("utf-8").split("\0")
    sensitive_names = [
        name
        for name in tracked
        if name
        and (
            name == ".env"
            or any(part in {".venv", ".cache", ".tools"} for part in name.split("/"))
            or (name.rsplit("/", 1)[-1].startswith(".env") and name != ".env.example")
        )
    ]
    current_findings, file_count = [], 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part in EXCLUDED or part.endswith(".egg-info") for part in path.relative_to(ROOT).parts
        ):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        file_count += 1
        for kind in inspect(path.read_bytes()):
            current_findings.append({"path": path.relative_to(ROOT).as_posix(), "type": kind})
    objects = {}
    for line in git("rev-list", "--objects", "--all").decode("utf-8").splitlines():
        fields = line.split(" ", 1)
        objects.setdefault(fields[0], fields[1] if len(fields) > 1 else "")
    ids = list(objects)
    types = (
        git("cat-file", "--batch-check=%(objecttype)", payload=("\n".join(ids) + "\n").encode())
        .decode()
        .splitlines()
    )
    selected = [sha for sha, kind in zip(ids, types, strict=True) if kind in ("blob", "commit")]
    stream = io.BytesIO(git("cat-file", "--batch", payload=("\n".join(selected) + "\n").encode()))
    history_findings = []
    for sha in selected:
        header = stream.readline().decode().split()
        raw = stream.read(int(header[2]))
        assert stream.read(1) == b"\n"
        for kind in inspect(raw):
            history_findings.append({"object": sha, "path": objects[sha], "type": kind})
    ignored = {}
    for name in (".env", ".venv/", ".cache/", ".tools/"):
        check = subprocess.run(["git", "check-ignore", "-q", name], cwd=ROOT, check=False)
        ignored[name] = check.returncode == 0
    manifest_path = ROOT / "FINAL_ACCEPTANCE/run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    modified = [
        name
        for name, digest in manifest["protected_historical_files"].items()
        if not (ROOT / name).exists()
        or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
    ]
    allowed_redaction = ["reports/logs/attempts/P0-1794285668763432800/P0-0.txt"]
    unexpected_changes = [name for name in modified if name not in allowed_redaction]
    bad = bool(
        current_findings
        or history_findings
        or sensitive_names
        or unexpected_changes
        or not all(ignored.values())
    )
    report = {
        "timestamp": utc_now(),
        "status": "BLOCKED" if bad else "PASS",
        "scanned_deliverable_files": file_count,
        "current_findings": current_findings,
        "reachable_commit_and_blob_objects": len(selected),
        "history_findings": history_findings,
        "sensitive_tracked_names": sensitive_names,
        "ignore_checks": ignored,
        "credential_leak_found": any(
            "credential" in f["type"] or f["type"] == "private_key"
            for f in current_findings + history_findings
        ),
        "known_path_privacy_issue": bool(history_findings),
        "history_rewrite_authorization": "Not assumed; explicit approval required before any rewrite or force push",
        "protected_historical_files": len(manifest["protected_historical_files"]),
        "changed_historical_files": modified,
        "unexpected_historical_changes": unexpected_changes,
        "privacy_redaction_evidence": "FINAL_ACCEPTANCE/privacy_redaction.json",
        "existing_credential_scanner": scan(ROOT),
        "limitations": "Pattern and configured-value scan, not a proof against every possible secret. Local .env, credential manager and ignored backups are intentionally never printed or packaged.",
    }
    write_json(ROOT / args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(2 if bad else 0)


if __name__ == "__main__":
    main()
