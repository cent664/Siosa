# ROLE: retriever — optional metadata filtering on retrieval results.

from __future__ import annotations

from poe_agent.retriever.models import RetrievedChunk


def filter_by_page_title(chunks: list[RetrievedChunk], prefix: str) -> list[RetrievedChunk]:
    if not prefix:
        return chunks
    prefix_lower = prefix.lower()
    return [
        c
        for c in chunks
        if str(c.metadata.get("page_title", "")).lower().startswith(prefix_lower)
    ]


def filter_poe1_only(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return [c for c in chunks if c.metadata.get("game") == "poe1"]
