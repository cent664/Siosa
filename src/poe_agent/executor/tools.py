# ROLE: executor — tool registry for agent actions.

from __future__ import annotations

from poe_agent.generator.answer import generate_answer_with_meta
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.pipeline import retrieve_for_query
from poe_agent.retriever.retrieval_debug import RetrievalDebugInfo


def wiki_search(
    query: str,
    user_question: str | None = None,
    extra_search_queries: list[str] | None = None,
    extra_title_probes: list[str] | None = None,
) -> tuple[list[RetrievedChunk], RetrievalDebugInfo | None]:
    chunks, _source, debug = retrieve_for_query(
        query,
        user_question=user_question,
        extra_search_queries=extra_search_queries,
        extra_title_probes=extra_title_probes,
    )
    return chunks, debug


def synthesize_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]] | None = None,
    summary: str = "",
) -> tuple[str, list[dict], dict]:
    return generate_answer_with_meta(
        question, chunks, history=history, summary=summary
    )
