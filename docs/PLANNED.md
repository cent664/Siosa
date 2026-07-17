# Planned changes

Siosa roadmap for a full **agentic stack** on a Path of Exile use case: tools, orchestration, MCP, memory, and user-gated evaluation — without expensive automatic multi-LLM loops. Self-hosted inference, quantization, and post-training live in a **separate project**, not here.

**Frozen starting build order:** [Roadmap baseline](planned-baseline.html) ([source](PLANNED_ROADMAP_BASELINE.md)) — do not strike items there; strike and update **this** page as work ships.

Edit this file, then run `python scripts/sync_docs.py` for browser HTML.

## Already in the app

- **RAG** — live poewiki fetch, chunking, citations.
- **Hybrid retrieval + rerank** — dense + BM25 (local mode), cross-encoder top passages; live / local / hybrid retrieval modes.
- **LangGraph (narrow)** — planner invents short search terms from the user question only, then one fused wiki lookup.
- **Score (LLM-as-judge)** — faithfulness, relevance, prompt adherence, context precision/recall; on-demand; post-hoc only (does not change the answer today).
- **Deploy** — FastAPI + React, Docker, GitHub Actions CI, Railway, OpenAI and Anthropic APIs.
- **Observability** — traces, timing, retrieval debug (always on in the UI).
- **Optional retrieval refine** — second wiki lookup when the first pass looks weak (`RETRIEVAL_REFINE_ENABLED`, **off by default**); heuristic gate today, not judge-driven.

## Planned

### Memory

- ~~**Memory summarization polish** — tune summary length/triggers for very long sessions (knobs adjustable).~~
- Remember citations/tools used in summary — not full wiki page dumps.

### Session, limits, and analytics

- ~~**Session memory** — SQLite turns + UI thread; expandable prior turns; history-aware wiki search (prior topics + citation page titles); rolling summary for long chats (recent window verbatim).~~
- ~~**Rate limits (scaffold)** — optional UTC daily Ask cap per IP (`RATE_LIMIT_ENABLED`, default off; 20/day when on).~~
- ~~**Operator analytics** — visit (1/IP/UTC day) + Asks to SQLite; private `/operator/analytics` dashboard (local and Railway when enabled + dashboard key).~~

### Tools and routing

- ~~**Ask composer under latest answer** — after the first reply, keep the text box / voice / Ask controls below the newest response (refresh for a new chat).~~
- **Source routing** — LangGraph chooses which tool(s), in what order, and when to stop. Simple mechanics Q&A stays a single wiki lookup; harder intents may call multiple tools then synthesize.
- **Tool registry** — treat live wiki fetch as the first tool; add **PoE Ninja** (prices, characters, builds, skill links) and **PoE DB / datamine** (numeric skill/item values the wiki may omit).
- **MCP** — expose the same tools behind an MCP server (names, JSON schemas, call/response). MCP is the protocol surface; LangGraph remains the orchestrator.

### Evaluation without auto-loops

- **Score + Revise** — keep on-demand Score; add a **Revise** action that uses those scores to improve the answer (for example rewrite for faithfulness, or re-retrieve then rewrite). Rate-limit revises per query (e.g. 1–5) so quality feedback stays user-gated and cheap.
- **Gold regression + MLflow (local)** — actually run the labeled gold set, note failure cases, and log metrics across versions with local MLflow (no cloud MLOps required).
- **Productize optional retrieval refine** — keep the weak-retrieval second lookup available (default off or only when retrieval looks weak); may later use evaluator signals as a gate.

### Product and cost controls

- **Tighten rate limits** — extend Ask caps to LLM/tool cost units when multi-tool and Revise land.
- **Response format customization** — user controls for brief vs detailed, bullets vs prose (today the system prompt is fixed).
- **Operator-only panels** — richer local views of analytics / private debug without a separate booth mode.

## Bonus

- **Context budgeting** — under a token budget, drop lowest-ranked chunks first; optional light compression of retrieved text before generate.
- **Non-retrieval compute tool** — e.g. a DPS calculator (structured stats in → number out) so the planner can combine retrieve + compute.
- **Smarter Revise policies** — faithfulness-only rewrite vs re-retrieve-then-rewrite depending on which scores are weak.
- **OOD / empty-retrieval refusals** — graceful “I don’t know” when the query is out of domain or retrieval returns nothing useful, without requiring a full judge pass.

## Discovered changes

- **Score/Revise product** — beyond scoring any expanded turn; full Revise loop stays on the Planned roadmap above.
- **Full query-fusion rewrite** — not planned; follow-ups use topic hints plus prior citation page titles / title probes.
- **Raw IPs / DIY geo / Railway→laptop analytics sync** — out of scope; hashed IP + proxy country headers only; view analytics on the host that recorded them.
- **Session summarization** — after each Ask, if turns exceed the recent verbatim window (`SESSION_MEMORY_RECENT_TURNS`, default 8), older turns are folded by an LLM into a rolling `sessions.summary`; the next prompt uses summary + recent turns + current question. This algorithm may need improvement / knobs adjustable later.
