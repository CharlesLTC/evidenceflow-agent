import pytest
from fastapi.testclient import TestClient

from evidenceflow.api import create_app


@pytest.fixture
def client(service_factory):
    with TestClient(create_app(service_factory())) as c:
        yield c


def test_api_health_and_complete_turn_trace(client):
    assert client.get("/health").status_code == 200
    response = client.post(
        "/ask", json={"question": "办公电脑申领审批需要多久？", "mode": "mock", "session_id": "api"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "COMPLETED" and result["mode"] == "mock"
    assert (
        client.get("/sessions/api?mode=mock").json()["turns"][0]["trace_id"] == result["trace_id"]
    )
    trace = client.get(f"/traces/{result['trace_id']}?mode=mock")
    assert trace.status_code == 200 and trace.json()["result"] == result
    assert client.get("/metrics").status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"question": " "},
        {"question": "Q", "mode": "fake_model"},
        {"question": "Q", "max_tool_calls": 13},
        {"question": "Q", "session_id": "../escape"},
    ],
)
def test_api_invalid_inputs_rejected(client, body):
    assert client.post("/ask", json=body).status_code == 422


def test_missing_model_returns_controlled_503_with_trace(client):
    response = client.post("/ask", json={"question": "Q", "mode": "live"})
    assert response.status_code == 503
    assert response.json()["status"] == "FAILED" and response.json()["error_code"] == "BLOCKED_LIVE"
    assert client.get(f"/traces/{response.json()['trace_id']}").status_code == 200


def test_missing_and_malformed_resource_ids(client):
    assert client.get("/sessions/missing").status_code == 404
    assert client.get("/traces/" + "0" * 32).status_code == 404
    assert client.get("/traces/not-a-uuid").status_code == 422


def test_business_tool_failure_is_not_marked_completed(client):
    response = client.post(
        "/ask", json={"question": "电脑申领", "mode": "mock", "fail_search_count": 2}
    )
    assert response.status_code == 200 and response.json()["status"] == "FAILED"
