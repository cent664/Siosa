# ROLE: executor — executes plan subtasks and accumulates retrieved context.

from __future__ import annotations

from poe_agent.executor.tools import wiki_search
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.retrieval_debug import RetrievalDebugInfo


def merge_retrieved_chunks(
    existing: list[RetrievedChunk],
    new_chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    seen: set[str] = {c.chunk_id for c in existing}
    merged = list(existing)
    for ch in new_chunks:
        if ch.chunk_id not in seen:
            seen.add(ch.chunk_id)
            merged.append(ch)
    return sorted(merged, key=lambda c: c.score, reverse=True)


def _tool_log_entry(
    query: str,
    results: list[RetrievedChunk],
    debug: RetrievalDebugInfo | None,
    *,
    refine_queries: list[str] | None = None,
    plan_queries: list[str] | None = None,
) -> dict:
    entry: dict = {
        "tool": "wiki_search",
        "query": query,
        "result_count": len(results),
    }
    if refine_queries is not None:
        entry["refine_queries"] = refine_queries
    if plan_queries is not None:
        entry["plan_queries"] = plan_queries
    if debug is not None:
        entry["retrieval_debug"] = debug.to_dict()
    return entry


def _collect_plan_search_extras(question: str, subtasks: list[dict]) -> list[str]:
    """Planner subtask strings merged into one fused wiki_search (excluding verbatim)."""
    q_norm = question.strip().casefold()
    extras: list[str] = []
    seen: set[str] = set()
    for task in subtasks:
        if task.get("action", "retrieve") == "synthesize":
            continue
        rq = str(task.get("query", "")).strip()
        if not rq:
            continue
        key = rq.casefold()
        if key == q_norm or key in seen:
            continue
        seen.add(key)
        extras.append(rq)
    return extras


def execute_subtasks(
    question: str,
    subtasks: list[dict],
    extra_search_queries: list[str] | None = None,
    extra_title_probes: list[str] | None = None,
) -> tuple[list[RetrievedChunk], list[dict]]:
    extras = _collect_plan_search_extras(question, subtasks)
    if extra_search_queries:
        seen = {e.casefold() for e in extras}
        q_norm = question.strip().casefold()
        for eq in extra_search_queries:
            key = eq.strip().casefold()
            if not key or key == q_norm or key in seen:
                continue
            seen.add(key)
            extras.append(eq.strip())
    results, debug = wiki_search(
        question,
        user_question=question,
        extra_search_queries=extras or None,
        extra_title_probes=extra_title_probes,
    )
    tool_log = [
        _tool_log_entry(
            question,
            results,
            debug,
            plan_queries=extras or None,
        )
    ]
    return results, tool_log


def execute_refine_retrieval(
    question: str,
    refine_queries: list[str],
) -> tuple[list[RetrievedChunk], list[dict]]:
    """One fused live retrieval pass using LLM-refined short queries."""
    if not refine_queries:
        return [], []
    results, debug = wiki_search(
        question,
        user_question=question,
        extra_search_queries=refine_queries,
    )
    tool_log = [_tool_log_entry("refine", results, debug, refine_queries=refine_queries)]
    return results, tool_log
