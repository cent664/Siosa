# ROLE: retriever — index status helpers.

from __future__ import annotations

from poe_agent.retriever.ingest import load_chunks


def is_index_ready() -> bool:
    try:
        from poe_agent.retriever.embed import get_chroma_collection

        return get_chroma_collection().count() > 0
    except Exception:
        return False


def get_chunk_count() -> int:
    return len(load_chunks())
