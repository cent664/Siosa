Newest first. Each entry uses the same format: a short title and a few bullets on what changed and why it mattered. Edit this file, then run `python scripts/sync_docs.py` for browser HTML.

## 2026-07-16 — Planned page aligned to List 1 roadmap

- Docs — Rewrote Planned page as Already / Planned / Bonus: multi-tool routing, memory, Score+Revise, gold+MLflow, rate limits; removed Siosa vLLM/performance deferred items.

## 2026-07-16 — Planned page aligned to List 1 roadmap

- Docs — Rewrote Planned page as Already / Planned / Bonus: multi-tool routing, memory, Score+Revise, gold+MLflow, rate limits; removed Siosa vLLM/performance deferred items.

## 2026-07-16 — Planned page: agentic roadmap

- Docs — Expanded Planned page with current-state summary and roadmap: multi-source tools (wiki, PoE Ninja, datamine), richer planning, MCP, session memory, performance.
- Docs — Clarified iterative keyword mining vs existing heuristic refine; portfolio goal for full agent stack on PoE use case.

## 2026-07-15 — Planned changes page and horizontal overview

- Docs — New Planned page (`docs/PLANNED.md` → `planned.html`): response-format customization, optional retrieval refine, booth vs full UI.
- Docs — Architecture overview flowchart is left-to-right; nav/footer link to Planned.

## 2026-07-15 — Architecture overview and stub-free docs

- Docs — App-level overview flowchart under the Architecture title (Harness → planner → live retrieval → generation → on-demand evaluator).
- Docs — Stub removed from visitor provider table and interactive pipeline copy; Claude and GPT-4 only.
- Docs — Clarified one-shot search-term planning, no chat memory, and post-hoc scoring that does not loop back.
- Docs — Dropped the “full wiki” disclaimer; planning copy starts with “A planner” (no provider preface).

## 2026-07-15 — Node.js prerequisite and npm path fallbacks

- Tooling — `start.bat` / `start.ps1` probe common Windows Node install paths before failing; clearer install message (`winget`, nodejs.org).
- Docs — Node.js LTS listed as prerequisite in `LAPTOP_SETUP.md` and `web/README.md`.

## 2026-07-15 — Always rebuild UI on start

- Tooling — `start.bat` / `start.ps1` always run `npm install` and `npm run build` before launching the API, so `web/dist` matches `web/src` after a `git pull`.

## 2026-06-09 — README trim, CI test fix, remove DEPLOY.md

- Docs — README drops “How it works” Mermaid; opens with developer architecture; “the agent runs at” wording; removed Doc sync section and DEPLOY.md.
- Docs — Developer sections renamed: Interactive pipeline and Judges (no “technical” suffix).
- Tests — Judge prompt-adherence test sets `JUDGE_PROVIDER=stub` so CI passes without `ANTHROPIC_API_KEY`.

## 2026-06-09 — Visitor Architecture docs, pipeline copy, UI prompt

- Docs — Split visitor Architecture (`docs/ARCHITECTURE.md` → `architecture.html`) from developer README (`docs/ARCHITECTURE_DEVELOPER.md` appended via `sync_docs.py`); no localhost in README header.
- Docs — Visitor page: +1pt typography; interactive pipeline uses plain language (no `POST /query` / env vars); Plan shows LangGraph for Claude/GPT-4, not “optional.”
- Docs — Technical pipeline detail in `pipeline-config-developer.json` and README developer section; CONTRIBUTING documents both config files.
- Web — Question prompt: “What are you curious about today?” on its own line after “May Reason preserve us.”

## 2026-06-04 — Architecture doc and Siosa UI polish

- Docs — Architecture page rewritten for the live pipeline; removed obsolete non-goals, scaling, gold-set, and local-vs-prod sections; added current retrieval algorithm and compact metrics copy.
- Docs — Interactive pipeline diagram updated (live fusion, on-demand judges); docs hub removed; Architecture and Changelog nav use a home icon back to the app.
- Web — Art assets moved to `art assets/`; `siosa_nobg` portrait; library background anchored to bottom; removed Ask loading text; footer links only Architecture and Changelog.
- Config — Production keeps `dev_ui_enabled` and OpenAI transcription; judges stay off the hot path via `INLINE_EVAL=false`.

## 2026-06-04 — Dev UI layout and metrics help

- Web — Answer shows first as plain markdown; pipeline timing bars and scoring timing (after **Score response**) sit below in a fixed order.
- Web — Timing bars use proportional widths capped at ~30% of the page; provider labels shortened (e.g. Sonnet 4.6, GPT-4o).
- Web — Sidebar removed; provider control under the title; documentation links moved to the footer.
- Web — **What do these metrics mean?** uses short bullets; each metric can expand **Show judge notes**. LLM call rows again show system, user, and response text when opened.

## 2026-06-04 — Voice via OpenAI Whisper

- Voice — Default `TRANSCRIBE_PROVIDER=openai` uses `whisper-1` with the same `OPENAI_API_KEY` as GPT-4.
- Voice — Browser mic still uploads WAV; local faster-whisper remains available when `TRANSCRIBE_PROVIDER=local`.
- Config — `.env.example` and deploy variable templates document OpenAI transcription for faster turnaround on laptops.

## 2026-06-04 — Live retrieval tuning

- Retrieval — Mechanic entities and topic terms drive fused MediaWiki queries; short mechanic strings run before the full user question.
- Retrieval — Up to four direct page-title probes plus title-overlap ranking of search hits before pages are fetched.
- Orchestrator — Planner retrieve subtasks merge into one fused `wiki_search` per pass instead of separate tool round-trips.
- Debug — Trace and tool panels still expose fused queries, title probes, and per-call retrieval debug.

## 2026-06-04 — Ollama removed from local dev

- Providers — Ollama mode and harness wiring removed from the repo; local stack is stub, Claude, or GPT-4 only.
- Config — `POE_ENABLE_OLLAMA`, `OLLAMA_*`, and judge routing to Ollama dropped from settings and deploy docs.
- Tests — Provider settings tests assert Ollama is not listed among available modes.

## 2026-06-04 — Judge context and pipeline timing

- Eval — Prompt-adherence judge now receives the same wiki excerpt blocks as faithfulness and relevance (not rules-only).
- Eval — Shared 1200-character chunk formatting across all five judges; trace includes chunk text for on-demand `POST /score`.
- API — LangGraph records `timing_ms` for plan, retrieval, and generation; scoring timing stays separate when judges run on demand.
- Web — Pipeline and scoring timing render as separate bar sections after Ask and after **Score response**.

## 2026-06-04 — Changelog accuracy

- Docs — Phase labels removed; May 28 milestones rewritten to match the same detail level as later entries.
- Correction — Gold-set regression and AWS Bedrock/S3 were scaffolded in the repo but never finished or used in the demo; entries below now say that explicitly.

## 2026-06-04 — Cloud-only providers and scoring UX

- Providers — Removed Ollama from the UI and judges; stub, Claude, and GPT-4 only, matching production.
- Eval — Inline judges off by default; optional **Score response** button and `POST /score` for on-demand scoring in dev.
- Eval — Judges now receive the same wiki excerpts as the answer model (shared context formatting).
- Web — Timing row shows plan, retrieval, and generation; `/health` uses `dev_ui_enabled` to hide trace UI on the public site.

## 2026-06-02 — Public demo on Railway

- Deploy — App live at **https://www.poesiosa.net/**; Docker image with rerank model baked in; Railway config and `DEPLOY.md`.
- Booth — Production UI shows answer and sources only; no per-ask judge calls, no quality panel, no trace or timing.
- Config — `DEPLOYMENT_PROFILE=production` sets booth defaults; verify script checks deploy variables.
- Docs — Conference-oriented architecture FAQ: live vs local retrieval, LangGraph routing, costs, and explicit non-goals.

## 2026-05-30 — Cloud reliability and documentation

- API — Cloud LLM failures return readable 502 messages instead of generic 500s.
- Eval — If inline judges fail, the answer still returns with scores marked skipped.
- Config — Choosing Claude or GPT-4 auto-aligns judges to that provider; default model updated to Claude Sonnet 4.6.
- Docs — Interactive pipeline diagram, slimmer architecture page, collapsible metrics; UI shows faithfulness, relevance, adherence, and context precision/recall.

## 2026-05-29 — Live wiki retrieval and quality

- Retrieval — Default `RETRIEVAL_MODE=live`: search poewiki per question, cache pages on disk, rerank chunks (no ingest required for Ask).
- Search — Several query variants per lookup (full question, keywords, optional direct page-title fetch).
- Quality — Title overlap filter reduces tangential pages; planner may run up to four wiki searches before answering.
- Debug — Trace shows fused searches, pages fetched, and chunk previews for each tool call.

## 2026-05-29 — React UI, voice, and observability

- UI — React + Vite replaces Streamlit on port 8000; `start.bat` builds the SPA and starts one API process.
- Voice — Browser mic upload; server transcribes with local faster-whisper or OpenAI Whisper.
- Providers — Claude and GPT-4 added beside stub and Ollama; API keys validated before enabling a mode.
- Trace — Every `/query` returns pipeline trace, LLM call log, and inline quality scores in dev.

## 2026-05-28 — Eval and deploy scaffolds

- Eval — `POST /evaluate` and a 10-row labeled gold file started for future retrieval checks; no automated regression suite was run.
- Deploy — Dockerfile, docker-compose, and GitHub Actions CI for build and test.
- Deploy — README and env docs for provider modes; Bedrock and S3 helpers exist in code but were not wired or validated for the demo.

## 2026-05-28 — Agent planner and multi-search

- Orchestrator — LangGraph flow: plan → retrieve → generate.
- Planner — Compare-style questions can trigger multiple `wiki_search` steps (e.g. full question plus short topic queries).
- Routing — Cloud providers use the graph; stub stays on a single linear retrieval pass.

## 2026-05-28 — Hybrid retrieval and rerank

- Search — Dense vectors (Chroma) plus BM25 keywords merged with reciprocal rank fusion.
- Rerank — Cross-encoder (`ms-marco-MiniLM-L-6-v2`) picks top passages for the LLM.
- Filter — PoE 1 metadata filter drops PoE 2 / wrong-game hits from the local index.

## 2026-05-28 — Curated wiki RAG

- Corpus — `poe-ingest` pulls 18 curated PoE 1 mechanic pages into chunks and ChromaDB.
- Pipeline — Linear retrieve-then-answer; stub mode returns wiki excerpts without an LLM.
- Providers — Ollama supported locally for free answers when a model is running.

## 2026-05-28 — Foundation

- Repo — Package layout, `pyproject.toml`, `.env.example`, architecture and changelog pages.
- API — FastAPI with `/health`, `/query`, and structured run logs.
- UI — First Streamlit front end for asking questions locally.
