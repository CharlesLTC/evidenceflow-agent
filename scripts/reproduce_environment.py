"""Install the frozen environment into a fresh ignored venv, then execute real checks."""
import json
import os
import subprocess
import sys
import time

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def main():
    directory = ROOT / ".cache/repro-venv"
    if directory.exists():
        raise RuntimeError("Fresh reproduction directory already exists; retain it and choose a new path")
    python = directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    commands = [
        [sys.executable, "-m", "venv", str(directory)],
        [str(python), "-m", "pip", "install", "-r", "requirements.txt", "--index-url", "https://pypi.org/simple", "--disable-pip-version-check"],
        [str(python), "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", ".[dev,embeddings]"],
        [str(python), "-m", "pip", "check"],
        [str(python), "-m", "pytest", "-q", "--junitxml=reports/logs/clean-pytest.xml"],
        [str(python), "-m", "evidenceflow.cli", "--help"],
    ]
    temporary = ROOT / ".cache/repro-temp"
    temporary.mkdir(parents=True, exist_ok=True)
    env = os.environ | {"PIP_CONFIG_FILE": "nul" if os.name == "nt" else "/dev/null",
                        "PYTHONIOENCODING": "utf-8", "TEMP": str(temporary), "TMP": str(temporary)}
    env.pop("PIP_EXTRA_INDEX_URL", None)
    records = []
    for index, command in enumerate(commands):
        start = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                encoding="utf-8", errors="replace", check=False, timeout=900)
        log = f"reports/logs/clean-{index}.txt"
        (ROOT / log).write_text(result.stdout + "\nSTDERR:\n" + result.stderr, encoding="utf-8")
        records.append({"argv": command, "exit_code": result.returncode,
                        "duration_seconds": time.perf_counter()-start, "log": log})
        print(f"clean step {index}: {result.returncode}", flush=True)
        if result.returncode:
            break
    report = {"timestamp": utc_now(), "status": "PASS" if len(records) == len(commands) and not any(r["exit_code"] for r in records) else "FAIL",
              "commands": records, "note": "Fresh venv from frozen requirements; model weights remain in project ignored cache; pytest does not call external models."}
    write_json(ROOT / "reports/clean_environment.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
