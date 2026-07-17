# List 1 build-order baseline (frozen)

This is the **starting roadmap** we agreed for improving Siosa. Keep it as historical reference; do **not** strike through items here as they ship. Track live progress in [`PLANNED.md`](PLANNED.md) / [planned.html](planned.html).

**Out of scope for Siosa (List 2):** vLLM, quantization, SFT/DPO, multimodal — separate project.

Edit this file only to correct the historical record. Run `python scripts/sync_docs.py` after edits.

---

## Phase 0 — Safety net (1–2 days)

- **Rate limits** (daily Ask / tool caps) — Protects cost before tools and Revise. Small change; do first.
- **Gold regression + local MLflow** — Run the existing gold set; log metrics. Baseline so later tool/memory/Revise work is measurable.

## Phase 1 — Conversation shape

- **Session memory (SQLite)** — Persist turns; pass recent history into Ask. Changes API/UI once — better before tools explode.
- **Memory summarization** — Only after memory works and you feel context pressure.

## Phase 2 — Real agent surface (core of List 1)

- **Tool registry + refactor wiki as tool #1** — Same behavior, new interface. Required before Ninja/datamine/MCP.
- **PoE Ninja tool** (one clear slice first: e.g. prices *or* character/build) — Proves multi-source without boiling the ocean.
- **LangGraph source routing** — Planner chooses wiki vs Ninja (order + stop). Simple Q → one tool; hard Q → multi-tool then synthesize.
- **PoE DB / datamine tool** — Second non-wiki source once routing works.
- **MCP wrapper** — Same tools, protocol surface — after tools are stable so you don’t dual-maintain.

## Phase 3 — Eval without expensive auto-loops

- **Score + Revise** (rate-limited revises per query) — Score already exists; Revise is the main new UX/API. Do after tools so Revise can optionally re-call tools.
- **Productize optional retrieval refine** — Wire/document the off-by-default second wiki lookup; optionally tie later to weak scores from Score.

## Phase 4 — Product polish (anytime, low dependency)

- **Response format customization**
- **Booth vs full UI** (if you still care for demos)

## Phase 5 — Bonus (after Planned “B” feels solid)

- **OOD / empty-retrieval “I don’t know”** (cheap, high resume value)
- **Context budgeting**
- **Smarter Revise policies**
- **Non-retrieval compute tool** (e.g. DPS) — nicest after multi-tool routing exists

---

## Why this order (short)

Cap cost early → measure with gold → memory before tools → tools before MCP → user-gated Score/Revise after tools → polish/bonus last.
