# Checklist

Living roadmap for Siosa's Library. Strike items or move them into **Already in the app** as they ship. Edit this file, then run `python scripts/sync_docs.py`.

Architecture stays separate and will be rewritten after these aggressive changes land. Self-hosted inference, DPO/RLAIF, and multi-source tools are **in scope for this project** (not a separate List 2).

## A. Already in the app

- **RAG** — live poewiki fetch, chunking, citations.
- **Live retrieval + cross-encoder rerank** — primary path.
- **Local hybrid (dense + BM25 + RRF)** — secondary/offline path (not the same as live).
- **LangGraph (narrow)** — search-term planning → one fused wiki lookup.
- **Five-metric LLM-as-judge (Score)** — context precision/recall, faithfulness, relevance, prompt adherence; post-hoc, on-demand.
- **Deploy** — FastAPI / React / Docker / CI / Railway / OpenAI & Anthropic.
- **Observability** — traces, timing, retrieval debug.
- **Optional retrieval refine** — exists in code, **off by default**.
- **Session memory** — SQLite turns, history-aware search, rolling chat summarization.
- **Rate-limit scaffold** — code exists, default **off** (enabling/tuning still Planned).
- **Operator analytics** — visit/Ask tracking to SQLite; private dashboard.
- **Retrieval heuristics (shipped)** — parallel wiki I/O, prior-page follow-ups, link expand, topic-switch gate, structure-aware tables, chunk diversity, larger top-N.

## B. Planned (main learn-by-building)

Implementation notes for future agents: prefer **user-gated** or **capped** LLM calls (Score + Revise, rate limits) over automatic multi-judge loops. New tools should share one **tool registry** interface so LangGraph can route without hardcoding every call site. Do not require AWS Bedrock/S3; SQLite/local disk and rented GPU weekends are enough for demos.

### Tools and sources

- **Tool registry** — register **live wiki** as tool #1 (same behavior, shared interface); then add more tools. Today the main path *is* live wiki search; this step makes it a named tool so Ninja/PoEDB/Cargo plug in the same way.
- **Cargo API** — structured wiki data (distinct from HTML live parse / MediaWiki search).
- **PoE Ninja** — prices / builds / characters (one slice first: e.g. prices *or* character/build). Likely API or scrape → normalize → optional local store/vectors.
- **PoE DB / datamine** — numeric skill/item values the wiki may omit. Same pattern: fetch/scrape, store, expose as a tool.
- **Source routing (LangGraph)** — which tool(s), order, stop; simple QA → one tool; hard QA → multi-tool then synthesize. Middle ground OK: light keyword rules for obvious cases, LLM for the rest; **Revise** recovers from bad tool choice without an auto loop.
- **MCP (and/or scrapers + indexes)** — protocol/wrappers for Ninja/PoEDB (and Cargo if useful). One MCP *server* with multiple tools is fine; MCP is optional portability/resume surface once Python tools work.

### Wiki offline cache / freshness

- **Local full(ish) wiki store + vectors** — answer from local cache for speed when possible.
- **On-Ask freshness check** — for pages touched by the query, if last fetch older than ~2–4 weeks, re-download those pages.
- **Periodic re-ingest** — e.g. every 1–4 months, batch re-download / re-vectorize.
- Keep **live search** as fallback on cache miss or when freshness requires it. This is not the same as today’s tiny 18-page seed index; it is a broader offline corpus with TTL.

### Memory / context

- **Summary contents polish** — citations/tools used in rolling summary (not full page dumps).
- **Context compression of retrieved chunks** — compress passages before generate (separate from chat summarization). Distinct from Bonus “context budgeting” (drop lowest-ranked chunks under a token budget).

### Eval (no expensive auto-loops)

- **Score + Revise** — Revise uses scores to improve answer; rate-limit revises per query (e.g. 1–5). Score already exists; Revise is new API/UX (rewrite and/or re-retrieve then rewrite).
- **Gold regression + local MLflow** — batch-run `gold.jsonl`, failure notes, version tracking. Offline rigor, not the Score button.
- **Productize optional retrieval refine** — gated weak-retrieval second lookup (`RETRIEVAL_REFINE_ENABLED`); optionally later tie to weak Score signals.

### Product / cost

- **Enable and tune rate limits** — real daily Ask/tool caps on the existing scaffold (`RATE_LIMIT_ENABLED`).
- **Response format customization** — brief/detailed, bullets/prose (system prompt is fixed today).
- **Booth vs full UI** and/or **richer operator-only panels** — booth mode was removed from code earlier; either restore a minimal public UI or deepen the private operator analytics/debug views.

### Model side (in-scope)

- **Self-hosted open weights** (e.g. Llama) via rented GPU — **vLLM** serving + **quantization** as an experimental provider mode alongside Claude/GPT-4. Prefer short GPU rentals for experiments; do not leave always-on GPUs on the public demo budget.
- **Fine-tuning** — **DPO** from judge-score preference pairs; **RLAIF** as the AI-feedback variant (training-time loop, distinct from Score+Revise at Ask time).

### Safety

- **Safety / red-teaming eval** — jailbreak / adversarial prompt tests against the live app.
- **Named guardrails** — schema validation, topic filters, grounding checks; **Constitutional AI**-style system constraints (behavioral rules), not only post-hoc scores.

## C. Bonus (after B feels solid)

Do these after multi-tool routing and Score+Revise feel solid. Keep them cheap (heuristics or one small tool).

- **Context budgeting** — under a token budget, drop lowest-ranked chunks first (overlaps lightly with chunk compression in B).
- **Non-retrieval compute tool** — e.g. DPS calculator (structured stats in → number out) so the planner can combine retrieve + compute.
- **Smarter Revise policies** — faithfulness-only rewrite vs re-retrieve-then-rewrite depending on which scores are weak.
- **OOD / empty-retrieval “I don’t know”** — graceful refusal when out of domain or retrieval is empty, without a full judge pass.
