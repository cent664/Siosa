# Planned changes

Ideas we deliberately left open. Edit this file, then run `python scripts/sync_docs.py` for browser HTML.

## Where we are today

The app is essentially **one tool**: live wiki fetch (`wiki_search`). LangGraph planning today is **query expansion from the user question only** — it invents short search terms before any pages are retrieved. There is no source selection, no multi-hop reasoning over page content, no chat memory, and no MCP. Evaluation scores are post-hoc and do not change retrieval or answers.

The goal below is to grow this into a full **agentic stack** on a concrete Path of Exile use case: tools, orchestration, MCP, memory, evaluation feedback, and performance — not a toy chat wrapper.

---

## Response format customization

Today every answer uses a fixed system prompt — length, tone, and layout are not user-configurable. We may add controls (for example brief vs detailed, bullets vs prose) so people can customize how answers are presented.

## Optional retrieval refinement

The pipeline can run a second wiki lookup when the first pass looks weak (`RETRIEVAL_REFINE_ENABLED`, off by default). This is close to “mine better keywords after first pages,” but it uses retrieval heuristics today, not the five LLM-as-judge scores. We still need to decide whether to leave it as a developer-only env flag, document it on the Architecture page, productize it, or later gate it on evaluator thresholds.

## Booth UI vs full UI

Full UI (timing, Score button, trace) is the default locally and on the public demo. Setting `DEV_UI_ENABLED=false` hides those panels and shows answer + sources only. We may later use that minimal “booth” layout on the cloud demo while keeping the full UI for local development.

---

## Agentic roadmap

### Tools (expand beyond live wiki)

- Treat **live wiki fetch** as the first tool in a small **tool registry** so the orchestrator can pick tools by intent.
- **PoE Ninja tool** — live economy and character data (trade prices, account/character listings, skill links, build details). Likely different APIs or schemas than MediaWiki.
- **PoE DB / datamine tool** — numeric skill and item values the wiki may not spell out (for example precise ignite scaling tables).
- **Source routing** — simple mechanics Q&A defaults to wiki; prices, builds, and characters lean toward Ninja; deep numeric mechanics lean toward datamine (or wiki plus datamine combined).

### Multi-step planning (beyond search-term expansion)

- Upgrade the planner from “extra search strings for one wiki pass” to **decide which tools to call**, in what order, and when to stop.
- Keep simple questions on a **single lookup path**; reserve multi-tool and multi-hop flows for harder intents.
- **Iterative keyword mining** — after the first retrieval, use retrieved chunks to propose better queries when quality is weak. Builds on the existing heuristic refine path; later may also use evaluator scores as a gate.

### MCP

- Add at least one **MCP server** for learning and demo value: wrap an existing server or **author a small MCP** whose tools mirror wiki / Ninja / datamine (names, JSON schemas, call/response boilerplate).
- MCP is the **protocol surface** for tools; LangGraph remains the **orchestrator** that invokes them.

### Memory (multi-turn)

- **Session memory** — include prior turns in later Asks (move from stateless to conversational).
- **Memory summarization** — compress older turns when context grows so follow-ups stay coherent without blowing the context window.
- Define what is remembered (questions, answers, citations, tools used) and what is not (full wiki page dumps).

### Performance and scale

- Profile end-to-end latency (wiki fetch, rerank, and LLM calls dominate today).
- Optimize before stacking more tools: caching, parallel tool calls where safe, keep judges off the hot path, smaller or faster generation models.
- If agent loops multiply LLM calls, evaluate **high-throughput local serving (e.g. vLLM)** or lighter cloud models.
