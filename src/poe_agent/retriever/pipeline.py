# ROLE: retriever — end-to-end retrieval pipeline (hybrid + rerank + filters).

from __future__ import annotations

from poe_agent.harness.config import get_settings
from poe_agent.retriever.dense import dense_search
from poe_agent.retriever.filters import filter_poe1_only
from poe_agent.retriever.hybrid import hybrid_search
from poe_agent.retriever.ingest import load_chunks
from poe_agent.retriever.live import retrieve_live_for_query
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.rerank import rerank
from poe_agent.retriever.retrieval_debug import RetrievalDebugInfo
from poe_agent.retriever.store import is_index_ready


def _retrieve_local(query: str) -> list[RetrievedChunk]:
    if not load_chunks():
        return []

    if is_index_ready():
        candidates = hybrid_search(query)
    else:
        candidates = dense_search(query)

    candidates = filter_poe1_only(candidates)
    try:
        return rerank(query, candidates)
    except Exception:
        return candidates[: get_settings().rerank_top_n]


def _needs_live_fallback(local: list[RetrievedChunk]) -> bool:
    if not local:
        return True
    settings = get_settings()
    top_score = max((c.score for c in local), default=0.0)
    return top_score < settings.live_fallback_min_score


def _merge_local_live(
    local: list[RetrievedChunk],
    live: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    seen: set[str] = set()
    merged: list[RetrievedChunk] = []
    for chunk in sorted(local + live, key=lambda c: c.score, reverse=True):
        if chunk.chunk_id in seen:
            continue
        seen.add(chunk.chunk_id)
        merged.append(chunk)
    return merged[: get_settings().rerank_top_n]


def retrieve_for_query(
    query: str,
    user_question: str | None = None,
    extra_search_queries: list[str] | None = None,
) -> tuple[list[RetrievedChunk], str, RetrievalDebugInfo | None]:
    """Return (chunks, retrieval_source, debug). debug is set for live/hybrid live leg."""
    settings = get_settings()
    mode = settings.retrieval_mode.lower()
    user_q = user_question or query

    if mode == "live":
        chunks, debug = retrieve_live_for_query(
            query, user_question=user_q, extra_search_queries=extra_search_queries
        )
        return chunks, "live", debug

    if mode == "hybrid":
        local = _retrieve_local(query)
        if _needs_live_fallback(local):
            live_chunks, debug = retrieve_live_for_query(
                query, user_question=user_q, extra_search_queries=extra_search_queries
            )
            if live_chunks:
                for ch in local:
                    ch.metadata.setdefault("retrieval", "local")
                for ch in live_chunks:
                    ch.metadata["retrieval"] = "live"
                return _merge_local_live(local, live_chunks), "hybrid", debug
        for ch in local:
            ch.metadata.setdefault("retrieval", "local")
        return local, "local", None

    chunks = _retrieve_local(query)
    for ch in chunks:
        ch.metadata.setdefault("retrieval", "local")
    return chunks, "local", None
