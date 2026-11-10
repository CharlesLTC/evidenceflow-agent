"""Execute real checks, retain stdout and junit, then record an honest stage gate."""
import argparse
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def run_stage(stage, commands, *, blockers=None, evidence=None, changes=None):
    started = now()
    previous = ROOT / f"reports/gates/{stage}.json"
    if previous.exists():
        archive = ROOT / "reports/logs/attempts" / (stage + "-" + str(time.time_ns()))
        archive.mkdir(parents=True)
        shutil.copy2(previous, archive / "gate.json")
        for old in (ROOT / "reports/logs").glob(stage + "-*"):
            if old.is_file():
                shutil.copy2(old, archive / old.name)
    temp = ROOT / ".cache/tmp"
    temp.mkdir(parents=True, exist_ok=True)
    records = []
    for index, command in enumerate(commands):
        args = command["argv"] if isinstance(command, dict) else command
        allowed = command.get("allowed_exit_codes", [0]) if isinstance(command, dict) else [0]
        argv = [sys.executable if x == "python" else x for x in args]
        begin = time.perf_counter()
        proc = subprocess.run(argv, cwd=ROOT, capture_output=True, encoding="utf-8",
                              errors="replace", env=__import__('os').environ | {
                                  "PYTHONIOENCODING": "utf-8", "TEMP": str(temp), "TMP": str(temp),
                                  "PIP_CONFIG_FILE": "nul" if sys.platform == "win32" else "/dev/null"})
        log = ROOT / f"reports/logs/{stage}-{index}.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(proc.stdout + "\nSTDERR:\n" + proc.stderr, encoding="utf-8")
        records.append({"argv": args, "exit_code": proc.returncode,
                        "allowed_exit_codes": allowed,
                        "duration_seconds": time.perf_counter() - begin,
                        "log": str(log.relative_to(ROOT)).replace("\\", "/")})
        print(f"{stage} check {index}: exit={proc.returncode}; {log.name}", flush=True)
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    junit = ROOT / f"reports/logs/{stage}-pytest.xml"
    if junit.exists():
        for suite in ET.parse(junit).getroot().iter("testsuite"):
            for key in counts:
                counts[key] += int(suite.get(key, 0))
        counts["passed"] = counts["tests"] - sum(counts[k] for k in ("failures", "errors", "skipped"))
    failed = [r for r in records if r["exit_code"] not in r["allowed_exit_codes"]]
    report = {"stage": stage, "started_at": started, "finished_at": now(),
              "status": "FAIL" if failed else "BLOCKED" if blockers else "PASS",
              "commands": records, "test_counts": counts, "metrics": {},
              "evidence_paths": evidence or [], "errors": blockers or [],
              "changes_made": changes or []}
    (ROOT / "reports/gates").mkdir(parents=True, exist_ok=True)
    (ROOT / f"reports/gates/{stage}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with (ROOT / "CODEX_WORKLOG.md").open("a", encoding="utf-8") as f:
        f.write(f"\n## {stage} — {started} → {report['finished_at']} UTC\n\n")
        f.write(f"Status: {report['status']}; checks: {len(records)}; pytest: {counts}.\n\n")
        f.write("\n".join(f"- {x}" for x in (changes or []) + (blockers or [])) + "\n")
        f.write(f"\nEvidence: reports/gates/{stage}.json and reports/logs/{stage}-*.\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True)
    p.add_argument("--plan", required=True, help="JSON file with commands/blockers/evidence/changes")
    a = p.parse_args()
    report = run_stage(a.stage, **json.loads(Path(a.plan).read_text(encoding="utf-8-sig")))
    raise SystemExit(1 if report["status"] == "FAIL" else 0)

