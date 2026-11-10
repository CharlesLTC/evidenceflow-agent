"""Read actual GitHub and Git heads; the final receipt is ignored to avoid SHA self-reference."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def command(args):
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True, timeout=90
    ).stdout.strip()


def verify(record_publication=False):
    gh = shutil.which("gh") or str(ROOT / ".tools/gh/bin/gh.exe")
    metadata = json.loads(
        command([gh, "repo", "view", "--json", "nameWithOwner,url,isPrivate,defaultBranchRef"])
    )
    local = command(["git", "rev-parse", "HEAD"])
    remote = command(["git", "ls-remote", "origin", "HEAD"]).split()[0]
    github = command(
        [gh, "api", f"repos/{metadata['nameWithOwner']}/git/ref/heads/main", "--jq", ".object.sha"]
    )
    if not re.fullmatch(r"[a-f0-9]{40}", local) or not local == remote == github:
        raise RuntimeError("Local, remote HEAD and GitHub API commit do not match")
    readme_blob = command(
        [
            gh,
            "api",
            f"repos/{metadata['nameWithOwner']}/contents/README.md?ref=main",
            "--jq",
            ".sha",
        ]
    )
    clean = not command(["git", "status", "--porcelain"])
    result = {
        "status": "PASS",
        "timestamp": utc_now(),
        "github_url": metadata["url"],
        "private": metadata["isPrivate"],
        "local_commit_sha": local,
        "remote_head": remote,
        "github_api_head": github,
        "readme_blob_readable": readme_blob,
        "worktree_clean": clean,
        "reviewer_access": "Private repository; reviewer account not supplied, access must be granted separately.",
    }
    if record_publication:
        write_json(
            ROOT / "reports/github_delivery.json",
            {
                "url": metadata["url"],
                "private": metadata["isPrivate"],
                "verified_initial_commit_sha": local,
                "remote_head": remote,
                "github_api_head": github,
                "verified_at": result["timestamp"],
                "readme_blob_readable": readme_blob,
                "final_commit_receipt": "reports/delivery_verification.local.json",
                "reviewer_access": result["reviewer_access"],
            },
        )
    archive = ROOT.parent / "evidenceflow-agent-delivery.zip"
    if archive.exists():
        result["archive"] = str(archive)
        result["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    write_json(ROOT / "reports/delivery_verification.local.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-publication", action="store_true")
    verify(parser.parse_args().record_publication)
