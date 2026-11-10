"""Fresh final checks. Keeps prior canonical evidence and never changes acceptance criteria."""

import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from evidenceflow.config import ROOT, Settings
from evidenceflow.trace_writer import utc_now, write_json

FINAL = ROOT / "FINAL_ACCEPTANCE"
EXCLUDED = {".git", ".venv", ".cache", ".tools", "__pycache__", ".pytest_cache", ".ruff_cache"}


def eligible(path):
    return not any(
        part in EXCLUDED or part.endswith(".egg-info") for part in path.relative_to(ROOT).parts
    )


def copy_report(source, target):
    source = ROOT / source
    if source.exists():
        target = FINAL / target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def execute(module, *args, timeout=1200):
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    log = FINAL / f"logs/{stamp}-{module.replace('.', '-')}.txt"
    command = [str(Path(".venv/Scripts/python.exe")), "-m", module, *args]
    print(f"START {module}", flush=True)
    start = time.perf_counter()
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ | {"PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        output = process.stdout + "\nSTDERR:\n" + process.stderr
        code = process.returncode
    except subprocess.TimeoutExpired:
        output, code = "Explicit execution timeout exceeded. No success assumed.", 124
    # New logs cannot copy local credentials or private user-directory identifiers.
    settings = Settings.from_env()
    if settings.api_key:
        output = output.replace(settings.api_key, "[REDACTED_CREDENTIAL]")
    output = re.sub(r"S-1-5-21-[0-9-]+", "[REDACTED_WINDOWS_SID]", output)
    output = re.sub(r"(?i)[A-Z]:[\\/]Users[\\/][^\\/\s\"']+", "[REDACTED_USER_HOME]", output)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(output, encoding="utf-8")
    record = {
        "command": command,
        "exit_code": code,
        "seconds": time.perf_counter() - start,
        "status": "PASS" if code == 0 else "FAIL",
        "log": log.relative_to(ROOT).as_posix(),
    }
    with (FINAL / "commands.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"DONE {module}: exit={code}", flush=True)
    return record


def prepare():
    FINAL.mkdir(exist_ok=True)
    if (FINAL / "run_manifest.json").exists():
        return
    baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    # Preserve every mutable top-level and quality report before any experiment.
    files = list((ROOT / "reports").glob("*")) + list((ROOT / "reports/quality").glob("*"))
    for path in files:
        if path.is_file() and path.name != "delivery_verification.local.json":
            copy_report(path.relative_to(ROOT), "before/" + path.relative_to(ROOT).as_posix())
    protected = {}
    for prefix in (
        "reports/logs/attempts",
        "reports/critic_eval_runs",
        "reports/quality/runs",
        "reports/handoff",
        "examples",
    ):
        for path in (ROOT / prefix).rglob("*"):
            if path.is_file():
                protected[path.relative_to(ROOT).as_posix()] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    write_json(
        FINAL / "run_manifest.json",
        {
            "started_at": utc_now(),
            "baseline_commit": baseline,
            "protected_historical_files": protected,
            "model": Settings.from_env().model_name,
        },
    )


def integrity():
    required = [
        "README.md",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "src",
        "data",
        "tests",
        "examples",
    ]
    required += [
        f"docs/0{i}-{name}.md"
        for i, name in enumerate(
            ("requirements", "solution", "evaluation", "ai-usage", "retrospective"), 1
        )
    ]
    modules = [
        "agent_graph",
        "llm_client",
        "retriever",
        "embeddings",
        "query_rewrite",
        "document_store",
        "evidence_guard",
        "claim_conflicts",
        "tools",
        "session_store",
        "evidence_critic",
        "api",
        "cli",
        "decision_basis",
    ]
    available = sorted(p.stem for p in (ROOT / "src/evidenceflow").glob("*.py"))
    errors = []
    counts = {"python": 0, "json": 0, "jsonl_rows": 0}
    for path in ROOT.rglob("*"):
        if not path.is_file() or not eligible(path):
            continue
        try:
            if path.suffix == ".py":
                compile(path.read_text(encoding="utf-8-sig"), path.name, "exec")
                counts["python"] += 1
            elif path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8-sig"))
                counts["json"] += 1
            elif path.suffix == ".jsonl":
                for line in path.read_text(encoding="utf-8-sig").splitlines():
                    if line.strip():
                        json.loads(line)
                        counts["jsonl_rows"] += 1
        except Exception as error:
            errors.append(
                {"path": path.relative_to(ROOT).as_posix(), "error": type(error).__name__}
            )
    imports = {}
    for module in modules:
        try:
            importlib.import_module("evidenceflow." + module)
            imports[module] = "PASS"
        except Exception as error:
            imports[module] = type(error).__name__
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    commands = [
        execute("pip", "check"),
        execute("evidenceflow.cli", "--help"),
        execute("uvicorn", "--version"),
        execute("streamlit", "--version"),
    ]
    missing = [name for name in required if not (ROOT / name).exists()]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    startup = all(
        s in readme
        for s in (
            "evidenceflow.cli ask",
            "evidenceflow.api:app",
            "streamlit run ui/app.py",
            "18501",
            "STREAMLIT_SERVER_PORT",
        )
    )
    result = {
        "timestamp": utc_now(),
        "status": "PASS"
        if not missing
        and not errors
        and all(v == "PASS" for v in imports.values())
        and all(c["exit_code"] == 0 for c in commands)
        and startup
        else "FAIL",
        "required_files": required,
        "missing": missing,
        "validation_counts": counts,
        "errors": errors,
        "imports": imports,
        "package_modules": available,
        "cli_entry": config["project"]["scripts"],
        "dependencies": config["project"]["dependencies"],
        "optional_dependencies": config["project"]["optional-dependencies"],
        "readme_startup_commands_match": startup,
        "commands": commands,
    }
    write_json(FINAL / "F1_project_integrity.json", result)


def core():
    record = execute("pytest", "-q", "--junitxml=FINAL_ACCEPTANCE/F2_pytest_results.xml")
    path = FINAL / "F2_pytest_results.xml"
    if path.exists():
        suites = list(ET.parse(path).getroot().iter("testsuite"))
        counts = {
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        counts["passed"] = (
            counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        )
        counts["pytest_seconds"] = sum(float(s.get("time", 0)) for s in suites)
    else:
        counts = {}
    write_json(FINAL / "F2_pytest_summary.json", {**record, **counts})
    live = execute("scripts.run_acceptance", "--mode", "live")
    copy_report("reports/acceptance_results.live.json", "F3_live_acceptance.json")
    if live["exit_code"] == 0:
        execute("scripts.validate_live_evidence")
        copy_report("reports/live_branch_evidence.json", "F3_dynamic_paths.json")


def enhancements():
    from dataclasses import replace

    from evidenceflow.agent_graph import AgentService
    from scripts.quality_core import single_conflict

    official = json.loads((FINAL / "F3_live_acceptance.json").read_text(encoding="utf-8"))
    if official["status"] != "PASS":
        write_json(
            FINAL / "F4_enhancement_validation.json",
            {"status": "BLOCKED", "reason": "F3 did not pass"},
        )
        return
    settings = replace(Settings.from_env(), strategy="bm25", critic_enabled=False)
    service = AgentService(settings)
    rows = []
    try:
        for index in range(5):
            row = {"run": index + 1, **single_conflict(service)}
            rows.append(row)
            write_json(FINAL / "F4_tc02_runs.json", rows)
            print(
                f"TC02 fresh {index + 1}: {row['status']}, rejections={row['guard_rejections']}",
                flush=True,
            )
    finally:
        service.sessions.close()
    conflict = {
        "status": "PASS" if all(r["status"] == "PASS" for r in rows) else "FAIL",
        "passed": sum(r["status"] == "PASS" for r in rows),
        "total": 5,
        "success_rate": sum(r["status"] == "PASS" for r in rows) / 5,
        "guard_rejections": sum(r["guard_rejections"] for r in rows),
        "runs": rows,
    }
    write_json(FINAL / "F4_tc02_stability.json", conflict)
    records = [execute("scripts.quality_core", "--strategy", "hybrid", "--fallback-probe")]
    for name in ("hybrid_official", "hybrid_execution", "hybrid_fallback_live"):
        copy_report(f"reports/quality/{name}.json", f"F4_{name}.json")
    records += [execute("scripts.evaluate_retrieval"), execute("scripts.verify_retrieval_results")]
    for name in (
        "retrieval_metrics",
        "retrieval_details",
        "retrieval_failures",
        "retrieval_verification",
    ):
        copy_report(f"reports/{name}.json", f"F4_{name}.json")
    records += [execute("scripts.evaluate_critic"), execute("scripts.run_extended_live")]
    copy_report("reports/critic_evaluation.json", "F4_critic_evaluation.json")
    copy_report("reports/extended_live.json", "F4_extended_live.json")
    tc03 = []
    for label, report in (
        ("bm25", official),
        ("hybrid", json.loads((FINAL / "F4_hybrid_official.json").read_text(encoding="utf-8"))),
    ):
        for case in report["cases"]:
            if case["id"] == "TC03":
                trace = json.loads((ROOT / case["trace"]).read_text(encoding="utf-8"))
                rejected = [
                    e
                    for e in trace["events"]
                    if e.get("tool_name") == "submit_answer"
                    and not e.get("observation", {}).get("valid", False)
                ]
                tc03.append(
                    {"strategy": label, "case": case, "intermediate_guard_rejections": rejected}
                )
    history = json.loads(
        (FINAL / "before/reports/quality/tc02_stability.json").read_text(encoding="utf-8")
    )
    result = {
        "timestamp": utc_now(),
        "status": "PASS"
        if conflict["status"] == "PASS" and all(r["exit_code"] == 0 for r in records)
        else "FAIL",
        "commands": records,
        "tc02_fresh": conflict,
        "tc02_history": history,
        "tc03_current": tc03,
        "critic_protocol": "Fixed four controlled omissions plus two clean controls. Not a natural model error-rate estimate.",
        "criteria_changes": False,
        "external_retries": 0,
    }
    write_json(FINAL / "F4_enhancement_validation.json", result)


def checks():
    records = [
        execute("scripts.smoke_ui"),
        execute("scripts.verify_artifacts"),
        execute("scripts.security_scan"),
        execute("ruff", "check", "src", "scripts", "tests", "ui"),
    ]
    copy_report("reports/ui_smoke.json", "F5_mock_ui_cases.json")
    copy_report("reports/artifact_verification.json", "artifact_verification.json")
    write_json(FINAL / "final_checks.json", {"commands": records})


def main():
    temp = ROOT / ".cache/final-acceptance-temp"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ.update({"PYTHONIOENCODING": "utf-8", "TEMP": str(temp), "TMP": str(temp)})
    prepare()
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("all", "integrity"):
        integrity()
    if phase in ("all", "core"):
        core()
    if phase in ("all", "enhancements"):
        enhancements()
    if phase in ("all", "checks"):
        checks()


if __name__ == "__main__":
    main()
