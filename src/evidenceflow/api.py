import json
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Path, Response

from evidenceflow.agent_graph import AgentService
from evidenceflow.schemas import Answer, AskRequest


def create_app(service=None):
    @asynccontextmanager
    async def lifespan(app):
        owned = service is None
        app.state.service = service or AgentService()
        yield
        if owned:
            app.state.service.sessions.close()

    app = FastAPI(title="EvidenceFlow", version="0.1.0", lifespan=lifespan)
    if service is not None:
        app.state.service = service

    @app.get("/health")
    def health():
        s = app.state.service
        return {
            "status": "ok",
            "llm_configured": s.settings.live_blocker() is None,
            "documents": len(s.store.documents),
            "embedding_ready": (s.settings.root / ".cache/embeddings/manifest.json").exists(),
        }

    @app.post("/ask", response_model=Answer)
    def ask(request: AskRequest, response: Response):
        if request.mode == "fake_model":
            raise HTTPException(422, detail={"code": "FAKE_MODEL_TEST_ONLY"})
        try:
            result = app.state.service.ask(request)
        except Exception:
            raise HTTPException(503, detail={"code": "AGENT_SERVICE_UNAVAILABLE"}) from None
        if result.error_code and result.status == "FAILED":
            response.status_code = 503
        return result

    @app.get("/sessions/{session_id}")
    def session(
        session_id: Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,80}$")],
        mode: Literal["live", "mock"] = "live",
    ):
        turns = app.state.service.sessions.history(session_id, mode)
        if not turns:
            raise HTTPException(404, detail={"code": "SESSION_NOT_FOUND"})
        return {"session_id": session_id, "mode": mode, "turns": turns}

    @app.get("/traces/{trace_id}")
    def trace(
        trace_id: Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")],
        mode: Literal["live", "mock"] = "live",
    ):
        path = app.state.service.settings.root / f"examples/traces/{mode}/{trace_id}.json"
        if not path.exists():
            raise HTTPException(404, detail={"code": "TRACE_NOT_FOUND"})
        return json.loads(path.read_text(encoding="utf-8"))

    @app.get("/metrics")
    def metrics():
        root = app.state.service.settings.root
        result = {}
        for key, name in [
            ("retrieval", "retrieval_metrics.json"),
            ("acceptance", "acceptance_results.json"),
        ]:
            p = root / "reports" / name
            result[key] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        result["gates"] = [
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((root / "reports/gates").glob("P*.json"))
        ]
        return result

    return app


app = create_app()
