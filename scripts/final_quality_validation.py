"""Final actual regression, live scenarios, injected failures and artifact/security checks."""

import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def main():
    started = utc_now()
    temporary = ROOT / ".cache/quality-temp"
    temporary.mkdir(parents=True, exist_ok=True)
    env = os.environ | {
        "PYTHONIOENCODING": "utf-8",
        "EVIDENCEFLOW_ROOT": str(ROOT),
        "RETRIEVAL_STRATEGY": "bm25",
        "EVIDENCE_CRITIC_ENABLED": "false",
        "TEMP": str(temporary),
        "TMP": str(temporary),
    }
    commands = [
        [sys.executable, "-m", "pytest", "-q", "--junitxml=reports/quality/final-pytest.xml"],
        [sys.executable, "-m", "ruff", "check", "src", "scripts", "tests", "ui"],
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "-m", "scripts.run_acceptance", "--mode", "mock"],
        [sys.executable, "-m", "scripts.quality_core", "--strategy", "bm25"],
        [sys.executable, "-m", "scripts.quality_core", "--strategy", "hybrid"],
        [sys.executable, "-m", "scripts.run_extended_live"],
        [sys.executable, "-m", "scripts.validate_live_evidence"],
        [sys.executable, "-m", "scripts.verify_retrieval_results"],
        [sys.executable, "-m", "scripts.smoke_ui"],
        [sys.executable, "-m", "scripts.verify_quality_results"],
        [sys.executable, "-m", "scripts.security_scan"],
        [sys.executable, "-m", "scripts.verify_artifacts"],
    ]
    isolated = (
        ROOT / ".cache/repro-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if isolated.exists():
        commands += [
            [str(isolated), "-m", "pip", "check"],
            [str(isolated), "-m", "pytest", "-q", "--junitxml=reports/quality/isolated-pytest.xml"],
        ]
    records = []
    for i, command in enumerate(commands):
        begin = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                check=False,
            )
            output, code = proc.stdout + "\nSTDERR:\n" + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            output, code = "Command exceeded the fixed 600 second validation timeout", 124
        log = f"reports/quality/final-{i:02}.txt"
        (ROOT / log).write_text(output, encoding="utf-8")
        records.append(
            {
                "argv": command,
                "exit_code": code,
                "duration_seconds": time.perf_counter() - begin,
                "log": log,
            }
        )
        write_json(
            ROOT / "reports/quality/final_validation_progress.json",
            {"started_at": started, "commands": records},
        )
        print(f"Final check {i}: exit={code} ({log})", flush=True)
        if i == 0 and code:
            break
    counts = {}
    path = ROOT / "reports/quality/final-pytest.xml"
    if path.exists():
        suites = list(ET.parse(path).getroot().iter("testsuite"))
        counts = {
            k: sum(int(s.get(k, 0)) for s in suites)
            for k in ("tests", "failures", "errors", "skipped")
        }
        counts["passed"] = (
            counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        )
    result = {
        "started_at": started,
        "finished_at": utc_now(),
        "status": "PASS"
        if len(records) == len(commands) and all(r["exit_code"] == 0 for r in records)
        else "FAIL",
        "commands": records,
        "pytest": counts,
        "isolated_environment_note": "Previously created isolated locked environment rerun on current source; not claimed as a new fresh install in this round.",
    }
    write_json(ROOT / "reports/quality/final_validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
