# ROLE: harness — FastAPI application entrypoint.

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from poe_agent.harness.api.settings_routes import router as settings_router
from poe_agent.harness.config import get_effective_provider_mode
from poe_agent.harness.api.errors import map_query_exception
from poe_agent.harness.provider_health import (
    judge_provider_hint,
    judge_provider_reachable,
)
from poe_agent.harness.api.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ScoreRequest,
    ScoreResponse,
    TranscribeResponse,
)
from poe_agent.harness.config import get_effective_judge_provider, get_settings, deployment_hint
from poe_agent.harness.logging import configure_logging
from poe_agent.harness.speech.transcribe import TranscriptionError, transcribe_wav
from poe_agent.retriever.store import get_chunk_count, is_index_ready

configure_logging()

app = FastAPI(
    title="PoE Wiki Agent",
    description="Path of Exile 1 wiki-grounded Q&A API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_project_root = Path(__file__).resolve().parents[4]
_docs_dir = _project_root / "docs"
_web_dist = _project_root / "web" / "dist"

if _docs_dir.is_dir():
    app.mount("/docs", StaticFiles(directory=str(_docs_dir), html=True), name="docs")

app.include_router(settings_router)


def _live_retrieval_hint(settings) -> str:
    mode = settings.retrieval_mode.lower()
    if mode == "live":
        return "Live poewiki fetch per Ask — expect +2–8s retrieval latency."
    if mode == "hybrid":
        return "Hybrid retrieval: local index first; live fetch when local scores are weak."
    return ""


@app.get("/health/live")
def health_live() -> dict[str, str]:
    """Lightweight liveness probe for Railway (no Chroma/judge checks)."""
    return {"status": "ok"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        provider_mode=get_effective_provider_mode(),
        chroma_ready=is_index_ready(),
        chunk_count=get_chunk_count(),
        retrieval_mode=settings.retrieval_mode.lower(),
        live_retrieval_hint=_live_retrieval_hint(settings),
        inline_eval=settings.inline_eval,
        dev_ui_enabled=settings.dev_ui_enabled,
        deployment_profile=settings.deployment_profile,
        deployment_hint=deployment_hint(settings),
        judge_provider=get_effective_judge_provider(),
        judge_reachable=judge_provider_reachable(settings),
        judge_hint=judge_provider_hint(settings),
    )


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    from poe_agent.harness.api.query_service import handle_query

    try:
        return handle_query(body.question)
    except Exception as exc:
        raise map_query_exception(exc) from exc


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    from poe_agent.evaluator.service import run_evaluation

    return run_evaluation(body)


@app.post("/score", response_model=ScoreResponse)
def score(body: ScoreRequest) -> ScoreResponse:
    from poe_agent.harness.api.score_service import handle_score

    try:
        return handle_score(body)
    except Exception as exc:
        raise map_query_exception(exc) from exc


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload.")
    try:
        text = transcribe_wav(data)
    except TranscriptionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TranscribeResponse(text=text)


# SPA static UI — register after API routes so /query, /health, etc. are not shadowed.
if (_web_dist / "index.html").is_file():
    app.mount(
        "/",
        StaticFiles(directory=str(_web_dist), html=True),
        name="web",
    )


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "poe_agent.harness.api.app:app",
        host=settings.poe_api_host,
        port=settings.poe_api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
