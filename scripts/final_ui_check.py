"""Actual API/Streamlit startup and widget-to-live-Agent round trip; no browser layout claim."""

import json
import os
import socket
import subprocess
import sys
import time

import httpx
from streamlit.testing.v1 import AppTest

from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def free_port(preferred):
    errors = []
    for candidate in (preferred, 0):
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", candidate))
                return sock.getsockname()[1], errors
        except OSError as error:
            errors.append(
                {"port": candidate, "error_type": type(error).__name__, "errno": error.errno}
            )
    raise RuntimeError("No available loopback port")


def main():
    final = ROOT / "FINAL_ACCEPTANCE"
    cache = ROOT / ".cache/final-ui"
    cache.mkdir(parents=True, exist_ok=True)
    api_port, api_errors = free_port(8000)
    ui_port, ui_errors = free_port(18501)
    api_url, ui_url = f"http://127.0.0.1:{api_port}", f"http://127.0.0.1:{ui_port}"
    exclusions = subprocess.run(
        ["netsh", "interface", "ipv4", "show", "excludedportrange", "protocol=tcp"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    (final / "F5_port_exclusions.txt").write_text(exclusions.stdout, encoding="utf-8")
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "evidenceflow.api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "ui/app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(ui_port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
    ]
    env = os.environ | {"EVIDENCEFLOW_API_URL": api_url, "PYTHONIOENCODING": "utf-8"}
    env["TEMP"] = env["TMP"] = str(cache)
    handles, processes, cases = [], [], []
    previous = os.environ.get("EVIDENCEFLOW_API_URL")
    report = {
        "timestamp": utc_now(),
        "status": "BLOCKED",
        "api_url": api_url,
        "ui_url": ui_url,
        "port_binding_errors": api_errors + ui_errors,
        "cases": cases,
        "method": "Two actual child servers, HTTP health/page probes and Streamlit AppTest against actual HTTP API; not browser pixel QA",
        "commands": [[".venv/Scripts/python.exe", *c[1:]] for c in commands],
    }
    try:
        for index, command in enumerate(commands):
            handle = (cache / f"server-{index}.log").open("w", encoding="utf-8")
            handles.append(handle)
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            )
        with httpx.Client(trust_env=False, timeout=3) as client:
            for url in (api_url + "/health", ui_url + "/_stcore/health"):
                for _ in range(120):
                    try:
                        if client.get(url).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.25)
                else:
                    raise RuntimeError("Owned server failed readiness probe")
            health = client.get(api_url + "/health")
            page = client.get(ui_url)
            docs = client.get(api_url + "/docs")
            schema = client.get(api_url + "/openapi.json")
            report["http_probes"] = {
                "api_health": health.status_code,
                "health_body": health.json(),
                "api_docs": docs.status_code,
                "openapi": schema.status_code,
                "streamlit_page": page.status_code,
                "streamlit_health": client.get(ui_url + "/_stcore/health").status_code,
                "page_bytes": len(page.content),
            }
            assert all(response.status_code == 200 for response in (health, page, docs, schema))
            os.environ["EVIDENCEFLOW_API_URL"] = api_url
            at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=120).run()
            assert not at.exception and at.button(key="ask").disabled
            report["empty_input_disabled"] = True
            for mode, question, failures, expected in (
                ("live", "办公电脑申领审批需要多久？", 0, "COMPLETED"),
                ("mock", "差旅报销期限是多久？", 0, "NEEDS_CLARIFICATION"),
                ("mock", "公司的年终奖金是多少？", 0, "INSUFFICIENT_EVIDENCE"),
                ("mock", "办公电脑申领审批需要多久？", 2, "FAILED"),
            ):
                at.button(key="new_session").click().run()
                at.selectbox(key="mode").select(mode).run()
                at.selectbox(key="failures").select(failures).run()
                at.text_area(key="question").input(question).run()
                at.button(key="ask").click().run()
                assert not at.exception
                result = at.session_state["last_result"]
                trace_response = client.get(f"{api_url}/traces/{result['trace_id']}?mode={mode}")
                trace = trace_response.json()
                session_response = client.get(
                    f"{api_url}/sessions/{result['session_id']}?mode={mode}"
                )
                assert (
                    result["status"] == expected
                    and trace_response.status_code == session_response.status_code == 200
                )
                assert trace["result"] == result
                if mode == "live":
                    assert result["model_name"] != "mock" and result["citations"]
                    assert any(e["kind"] == "model_decision" for e in trace["events"])
                    assert any("原文" in e.label for e in at.expander)
                    assert len(at.json) >= len(trace["events"])
                if expected == "FAILED":
                    assert len(at.error) and not len(at.success)
                cases.append(
                    {
                        "mode": mode,
                        "question": question,
                        "fail_search_count": failures,
                        "expected": expected,
                        "actual": result["status"],
                        "status": "PASS",
                        "model": result["model_name"],
                        "trace": f"examples/traces/{mode}/{result['trace_id']}.json",
                        "output": f"examples/outputs/{mode}/{result['trace_id']}.json",
                        "citations": len(result["citations"]),
                        "trace_events": len(trace["events"]),
                        "ui_json_blocks": len(at.json),
                        "session_http_status": session_response.status_code,
                    }
                )
                write_json(final / "F5_ui_api_check.json", report)
            metrics = client.get(api_url + "/metrics")
            missing = client.get(api_url + "/traces/" + "0" * 32 + "?mode=live")
            invalid = client.post(api_url + "/ask", json={"question": "", "mode": "live"})
            assert (
                metrics.status_code == 200
                and missing.status_code == 404
                and invalid.status_code == 422
            )
            report["api_error_checks"] = {
                "metrics": metrics.status_code,
                "missing_trace": missing.status_code,
                "invalid_request": invalid.status_code,
            }
            at.button(key="new_session").click().run()
            at.text_input(key="backend_url").input("http://127.0.0.1:1").run()
            at.text_area(key="question").input("办公电脑申领审批需要多久？").run()
            at.button(key="ask").click().run()
            assert not at.exception and len(at.error) and "last_result" not in at.session_state
            report["disconnected_backend_shows_error"] = True
            report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error_type"] = type(error).__name__
        raise
    finally:
        if previous is None:
            os.environ.pop("EVIDENCEFLOW_API_URL", None)
        else:
            os.environ["EVIDENCEFLOW_API_URL"] = previous
        for process in processes:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for handle in handles:
            handle.close()
        report["owned_servers_stopped_after_check"] = True
        write_json(final / "F5_ui_api_check.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
