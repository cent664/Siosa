# ROLE: harness — FastAPI application entrypoint.

from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
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
from poe_agent.harness.config import (
    deployment_hint,
    get_effective_judge_provider,
    get_settings,
    operator_analytics_active,
)
from poe_agent.harness.logging import configure_logging
from poe_agent.harness.operator_analytics import (
    fetch_recent_events,
    fetch_summary,
    log_event,
    log_visit_once_per_day,
    render_analytics_dashboard_html,
)
from poe_agent.harness.rate_limit import check_and_increment_ask
from poe_agent.harness.speech.transcribe import TranscriptionError, transcribe_wav
from poe_agent.retriever.store import get_chunk_count, is_index_ready

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.rerank_warm_on_startup:
        try:
            from poe_agent.retriever.rerank import warm_reranker

            warm_reranker()
        except Exception:
            pass
    yield
    try:
        from poe_agent.retriever.wiki_client import close_http_client

        close_http_client()
    except Exception:
        pass


app = FastAPI(
    title="PoE Wiki Agent",
    description="Path of Exile 1 wiki-grounded Q&A API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded.strip():
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _country(request: Request) -> str:
    return (
        request.headers.get("cf-ipcountry")
        or request.headers.get("x-country-code")
        or ""
    ).strip()


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
        deployment_profile=settings.deployment_profile,
        deployment_hint=deployment_hint(settings),
        judge_provider=get_effective_judge_provider(),
        judge_reachable=judge_provider_reachable(settings),
        judge_hint=judge_provider_hint(settings),
        rate_limit_enabled=settings.rate_limit_enabled,
        rate_limit_asks_per_day=settings.rate_limit_asks_per_day,
        operator_analytics_active=operator_analytics_active(settings),
    )


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, request: Request) -> QueryResponse:
    from poe_agent.harness.api.query_service import handle_query

    decision = check_and_increment_ask(_client_ip(request))
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily Ask limit reached ({decision.limit} per UTC day). "
                "Try again after the next UTC midnight."
            ),
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    try:
        log_event(
            path="/query",
            action="ask",
            client_ip=_client_ip(request),
            country=_country(request),
        )
        return handle_query(body.question, session_id=body.session_id)
    except Exception as exc:
        raise map_query_exception(exc) from exc


@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    from poe_agent.evaluator.service import run_evaluation

    return run_evaluation(body)


@app.post("/score", response_model=ScoreResponse)
def score(body: ScoreRequest, request: Request) -> ScoreResponse:
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


@app.get("/operator/analytics", response_class=HTMLResponse)
def operator_analytics_dashboard(
    key: str = Query(default="", description="OPERATOR_DASHBOARD_KEY from .env"),
) -> HTMLResponse:
    """Private HTML summary of visits and Asks. Gated by OPERATOR_DASHBOARD_KEY."""
    settings = get_settings()
    if not operator_analytics_active(settings):
        raise HTTPException(status_code=404, detail="Not found")
    expected = (settings.operator_dashboard_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=401,
            detail="Set OPERATOR_DASHBOARD_KEY in .env (or Railway Variables) to enable this page.",
        )
    if not secrets.compare_digest(key.strip(), expected):
        raise HTTPException(status_code=401, detail="Invalid key")
    summary = fetch_summary(settings=settings)
    events = fetch_recent_events(limit=200, settings=settings)
    return HTMLResponse(content=render_analytics_dashboard_html(events, summary))


# SPA static UI — register after API routes so /query, /health, etc. are not shadowed.
_spa_index = _web_dist / "index.html"
if _spa_index.is_file():

    @app.get("/")
    def spa_root(request: Request) -> FileResponse:
        try:
            log_visit_once_per_day(
                client_ip=_client_ip(request),
                country=_country(request),
            )
        except Exception:
            pass
        return FileResponse(_spa_index)

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
