# ROLE: retriever — reciprocal rank fusion of dense and sparse results.

from __future__ import annotations

from poe_agent.harness.config import get_settings
from poe_agent.retriever.dense import dense_search
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.sparse import sparse_search


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]],
    k: int | None = None,
) -> list[RetrievedChunk]:
    rrf_k = k or get_settings().hybrid_rrf_k
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, RetrievedChunk] = {}

    for results in result_lists:
        for rank, chunk in enumerate(results, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            chunks_by_id[chunk.chunk_id] = chunk

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    out: list[RetrievedChunk] = []
    for cid, score in fused:
        ch = chunks_by_id[cid]
        out.append(
            RetrievedChunk(
                chunk_id=ch.chunk_id,
                text=ch.text,
                metadata=ch.metadata,
                score=score,
            )
        )
    return out


def hybrid_search(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k or get_settings().retrieval_top_k
    dense = dense_search(query, top_k=k)
    sparse = sparse_search(query, top_k=k)
    return reciprocal_rank_fusion([dense, sparse])[:k]
