# Orchestrator (LangGraph)

Phase 4 moves multi-step reasoning here. The graph is:

`plan` → `execute` → `generate` → END

Linear RAG remains as a fallback path in `harness/api/query_service.py`; typical Claude/GPT-4 Asks use LangGraph.
