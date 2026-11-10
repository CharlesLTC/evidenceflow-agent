"""Streamlit AppTest interacts with an actual local HTTP API, never a fake HTTP response."""

import json
import os
import socket
import threading
import time

import httpx
import uvicorn
from streamlit.testing.v1 import AppTest

from evidenceflow.agent_graph import AgentService
from evidenceflow.api import create_app
from evidenceflow.config import ROOT
from evidenceflow.trace_writer import utc_now, write_json


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    service = AgentService()
    server = uvicorn.Server(
        uvicorn.Config(create_app(service), host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, "API did not start"
    previous_url = os.environ.get("EVIDENCEFLOW_API_URL")
    os.environ["EVIDENCEFLOW_API_URL"] = f"http://127.0.0.1:{port}"
    cases = []
    try:
        at = AppTest.from_file(str(ROOT / "ui/app.py"), default_timeout=30).run()
        assert not at.exception
        scenarios = [
            ("办公电脑申领审批需要多久？", 0, "COMPLETED"),
            ("差旅报销期限是多久？", 0, "NEEDS_CLARIFICATION"),
            ("公司的年终奖金是多少？", 0, "INSUFFICIENT_EVIDENCE"),
            ("办公电脑申领审批需要多久？", 1, "COMPLETED"),
            ("办公电脑申领审批需要多久？", 2, "FAILED"),
        ]
        with httpx.Client(trust_env=False) as client:
            assert client.get(f"http://127.0.0.1:{port}/health").status_code == 200
            for question, failure_count, expected in scenarios:
                at.button(key="new_session").click().run()
                at.selectbox(key="mode").select("mock").run()
                at.selectbox(key="failures").select(failure_count).run()
                at.text_area(key="question").input(question).run()
                at.button(key="ask").click().run()
                assert not at.exception
                result = at.session_state["last_result"]
                assert result["status"] == expected
                trace_response = client.get(
                    f"http://127.0.0.1:{port}/traces/{result['trace_id']}?mode=mock"
                )
                assert trace_response.status_code == 200
                assert trace_response.json()["result"] == result
                if expected == "FAILED":
                    assert len(at.error) >= 1 and len(at.success) == 0
                cases.append(
                    {
                        "question": question,
                        "fail_search_count": failure_count,
                        "expected": expected,
                        "actual": result["status"],
                        "mode": "mock",
                        "trace": f"examples/traces/mock/{result['trace_id']}.json",
                        "status": "PASS",
                    }
                )
        result = {
            "timestamp": utc_now(),
            "status": "PASS",
            "method": "Streamlit AppTest + actual loopback HTTP uvicorn API",
            "cases": cases,
            "limitations": "AppTest inspects widgets and state, not browser pixel layout. Model mode is explicitly mock for repeatability.",
        }
        write_json(ROOT / "reports/ui_smoke.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        if previous_url is None:
            os.environ.pop("EVIDENCEFLOW_API_URL", None)
        else:
            os.environ["EVIDENCEFLOW_API_URL"] = previous_url
        server.should_exit = True
        thread.join(10)
        service.sessions.close()


if __name__ == "__main__":
    main()
