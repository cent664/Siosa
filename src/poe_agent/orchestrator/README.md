# Orchestrator (LangGraph)

Phase 4 moves multi-step reasoning here. The graph is:

`plan` → `execute` → `generate` → END

Linear RAG in Phase 2–3 lives in `harness/api/query_service.py` until the corpus is indexed and provider mode is not `stub`/`linear`.
