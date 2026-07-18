# ROLE: retriever — cross-encoder reranking of candidate chunks.

from __future__ import annotations

from poe_agent.harness.config import get_settings
from poe_agent.retriever.models import RetrievedChunk

_reranker = None


def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder

        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def warm_reranker() -> None:
    """Load the cross-encoder once at API startup so the first Ask is not cold."""
    model = _get_reranker()
    model.predict([["warmup", "Path of Exile wiki passage warmup"]])


def rerank(query: str, chunks: list[RetrievedChunk], top_n: int | None = None) -> list[RetrievedChunk]:
    if not chunks:
        return []
    n = top_n or get_settings().rerank_top_n
    model = _get_reranker()
    pairs = [[query, c.text] for c in chunks]
    scores = model.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: float(x[1]), reverse=True)
    return [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            metadata=c.metadata,
            score=float(s),
        )
        for c, s in ranked[:n]
    ]
