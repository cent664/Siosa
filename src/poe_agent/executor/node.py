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
) -> dict:
    entry: dict = {
        "tool": "wiki_search",
        "query": query,
        "result_count": len(results),
    }
    if refine_queries is not None:
        entry["refine_queries"] = refine_queries
    if debug is not None:
        entry["retrieval_debug"] = debug.to_dict()
    return entry


def execute_subtasks(
    question: str,
    subtasks: list[dict],
) -> tuple[list[RetrievedChunk], list[dict]]:
    all_chunks: list[RetrievedChunk] = []
    seen_ids: set[str] = set()
    tool_log: list[dict] = []

    for task in subtasks:
        action = task.get("action", "retrieve")
        if action == "synthesize":
            continue
        query = task.get("query", question)
        results, debug = wiki_search(query, user_question=question)
        tool_log.append(_tool_log_entry(query, results, debug))
        for ch in results:
            if ch.chunk_id not in seen_ids:
                seen_ids.add(ch.chunk_id)
                all_chunks.append(ch)

    return all_chunks, tool_log


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
