import json

from fastapi.testclient import TestClient

from evidenceflow.api import app

if __name__ == "__main__":
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/ask", json={"question": "办公电脑申领审批需要多久？", "mode": "mock"}
        )
        assert response.status_code == 200 and response.json()["status"] == "COMPLETED"
        result = response.json()
        assert client.get(f"/traces/{result['trace_id']}?mode=mock").status_code == 200
        print(json.dumps(result, ensure_ascii=False, indent=2))
