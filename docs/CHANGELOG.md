## 2026-06-02 — Architecture conference FAQ

- Docs — `ARCHITECTURE.md`: booth pitch, live vs local hybrid, multi-query fusion vs LangGraph, routing table, chunk defaults, gold eval summary, deploy/cost snapshot, explicit non-goals; mermaid retrieve label fix.
- Docs — `pipeline-config.json`: interactive stages 0.3–0.7 aligned (five inline judges, planner multi-search, production Answer+Sources UI, `chroma_ready` note).

## 2026-06-02 — Production env profile

- Config — `DEPLOYMENT_PROFILE=production` applies booth defaults on Railway (`INLINE_EVAL=false`, `POE_ENABLE_OLLAMA=false`, cloud judge/provider when keys set).
- API — `/health` returns `deployment_hint` when booth mode is not active.
- Deploy — Verify script checks `inline_eval`, `enable_ollama`, and deployment hints.

## 2026-06-02 — Production booth mode (poesiosa.net)

- Deploy — Live at **https://www.poesiosa.net/** (custom domain on Railway).
- Config — `INLINE_EVAL=false` on production skips inline judge LLM calls; booth UI hides scores, trace, and timing (Answer + Sources only).
- Config — `POE_ENABLE_OLLAMA=false` on production hides Ollama from the provider dropdown; local dev keeps Ollama via `POE_ENABLE_OLLAMA=true`.
- API — `/health` exposes `inline_eval` and `enable_ollama` for frontend booth vs dev UI.
- CI — Fix Ruff lint errors (unused imports in src/tests).
- Deploy — Railway variable checklist for Claude/GPT-4 API keys on production.

## 2026-06-02 — Railway deployment

- Deploy — `railway.toml`, `DEPLOY.md`, Dockerfile PORT + pre-baked rerank model for Railway hosting.

## 2026-05-29 — Trace debug UI

- Web UI — Agent reasoning trace shows retrieval summary, structured plan/tool/chunk tables, and per-call fused searches + pages fetched.
- API — `retrieval_debug` on tool_calls; chunk trace includes `fetch_reason`, `search_query`, `chunk_id`; `retrieval_mode` / `retrieval_config` on trace.

## 2026-05-29 — Live retrieval quality

- Retrieval — Multi-query fusion per `wiki_search`: verbatim user question, subtask query, keyword variants, direct title probe; rerank scored against user question.
- Retrieval — Title overlap filter downranks tangential pages (e.g. Ruthless mode mentioning Pantheon).
- Planner — Verbatim question always first retrieve subtask; short variant queries only; up to 4 subtasks.
- Retrieval — Optional `RETRIEVAL_REFINE_ENABLED` gate + one LLM refine pass (LangGraph and linear).

## 2026-05-29 — Live poewiki retrieval

- Retrieval — `RETRIEVAL_MODE=local|live|hybrid` (default **live**): search and fetch poewiki at Ask time with disk cache and cross-encoder rerank.
- Retriever — `wiki_client.py` shared MediaWiki helpers; `live.py` for query-time fetch; ingest refactored to reuse the client.
- API — Health and query trace expose `retrieval_mode` / `retrieval_source`; sidebar shows live-mode latency hint.
- Docs — Architecture and interactive pipeline updated for live retrieval.

## 2026-05-30 — Anthropic Sonnet 4.6

- Config — `ANTHROPIC_MODEL` set to `claude-sonnet-4-6` (replaces deprecated `claude-sonnet-4-20250514`).

## 2026-05-30 — Judge provider alignment

- Config — Selecting Claude or GPT-4 in the UI auto-sets judges to the same cloud provider (no Ollama required for scoring).
- Config — Updated `ANTHROPIC_MODEL` default; fix deprecated model id in `.env`.

## 2026-05-30 — Cloud provider error handling

- API — `/query` maps LLM/network errors to 502 with readable `detail` (not generic 500).
- API — Health and provider settings expose `judge_provider`, `judge_reachable`, and hints when Ollama judges are down.
- Eval — Inline judge failures return the answer with skipped scores instead of failing the whole request.
- Config — Default `ANTHROPIC_MODEL` updated; `.env.example` documents `JUDGE_PROVIDER` for cloud-only setups.

## 2026-05-30 — Docs and architecture refresh

- Docs — Interactive pipeline diagram in `architecture.html` (hover details, faded alternative paths).
- Docs — Slimmer `ARCHITECTURE.md`: one LR Mermaid flow, removed code map and per-component I/O tables.
- Changelog — Bullet entries use `Label — description`; HTML renders proper lists (no raw `**Config:**`).
- Collapsible — Scaling and quality metrics sections collapsed by default in browser docs.
- Docs UX — Collapsible sections render Markdown tables; pipeline uses wing layout and fixed detail strip.
- Docs UX — Quality metrics split into retrieval (Evaluate) vs generation (inline Ask); enriched learning copy.
- Eval — Removed inline verbosity and hallucination risk; UI shows faithfulness, relevance, prompt adherence only.
- Eval — Inline LLM context precision and context recall on every Ask (shown with generation scores).
- Web UI — Voice control is mic icon only (no Record label).
- Docs UX — Pipeline alternatives in hover dropdown; seven steps fit page width without horizontal scroll.

## 2026-05-29 — React UI replaces Streamlit

- Web UI — React + Vite SPA at `http://127.0.0.1:8000/` (single FastAPI process).
- Removed — Streamlit, port 8501, `streamlit_app.py`.
- Voice — Browser `MediaRecorder` and `POST /transcribe`.
- Launcher — `start.bat` builds `web/dist` if needed, then uvicorn only.
- Docker — Multi-stage image includes compiled web UI.

## 2026-05-29 — Voice UX (Streamlit era)

- Voice — Record / Stop beside Ask; auto-transcribe into question field.
- Enter — Submits question without Ctrl+Enter.

## 2026-05-29 — Voice transcription (STT)

- Speech — `harness/speech/transcribe.py` with local faster-whisper or OpenAI Whisper API.
- API — `POST /transcribe` multipart WAV upload.
- Config — `TRANSCRIBE_PROVIDER`, `TRANSCRIBE_MODEL` in `.env.example`.
- Install — `pip install -e ".[speech]"` for offline STT.

## 2026-05-29 — UI polish, metrics guide, diagram fixes

- Form — Enter / Ctrl+Enter submits question (Streamlit).
- UI — Compact quality and timing tables.
- Docs — Metrics reference, scaling guide, Mermaid fix in `sync_docs.py`.

## 2026-05-29 — Multi-provider LLM, trace, inline quality scores

- Providers — Claude and GPT-4 alongside stub and Ollama; UI validation for API keys.
- Trace — `trace` and `llm_calls` on every `/query`.
- Inline eval — Faithfulness, relevance, verbosity, adherence (`JUDGE_PROVIDER` default ollama).
- Config — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `INLINE_EVAL`, `JUDGE_PROVIDER` in `.env.example`.

## 2026-05-29 — Docs, launcher, and UX

- Launcher — `start.bat` / `start.ps1` one-click API (later: React UI on same port).
- UI — Runtime provider toggle without editing `.env`.
- Docs — Served at `http://127.0.0.1:8000/docs/`; sync via `scripts/sync_docs.py`.

## 2026-05-28 — Phase 6 — Production hygiene

Bedrock adapters, optional S3 sync, Dockerfile, docker-compose, GitHub Actions CI. README covers deploy and `POE_PROVIDER_MODE`.

## 2026-05-28 — Phase 5 — Evaluator

`POST /evaluate` with retrieval P/R, LLM judges, extraction overlap. Gold set in `knowledge/eval/gold.jsonl`.

## 2026-05-28 — Phase 4 — LangGraph orchestrator

Planner → executor → generator; compare questions trigger multiple `wiki_search` calls.

## 2026-05-28 — Phase 3 — Hybrid retrieval + rerank

BM25 + dense vectors with RRF; cross-encoder reranking; PoE1 metadata filter.

## 2026-05-28 — Phase 2 — Wiki RAG pipeline

Curated ingest (`poe-ingest`), ChromaDB, linear RAG. Stub excerpts or Ollama answers.

## 2026-05-28 — Phase 1 — Local UI + API

First web UI (Streamlit) and FastAPI `/health`, `/query`, structured run logs.

## 2026-05-28 — Phase 0 — Skeleton

Package layout, `pyproject.toml`, architecture and changelog pages, `.env.example`.
