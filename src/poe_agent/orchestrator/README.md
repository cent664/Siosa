# Orchestrator (LangGraph)

Every Ask with retrieval available runs:

`plan` → `execute` (one fused wiki lookup) → `gate` → optional `refine` / `refine_execute` → `generate` → END

Refine only runs when `RETRIEVAL_REFINE_ENABLED=true`. Implementation: `graph.py`, invoked from `harness/api/query_service.py`.
