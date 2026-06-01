# ROLE: retriever — BM25 keyword search over chunk corpus.

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from poe_agent.harness.config import get_settings
from poe_agent.retriever.ingest import load_chunks
from poe_agent.retriever.models import RetrievedChunk

_bm25_cache: tuple[BM25Okapi, list] | None = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _get_bm25():
    global _bm25_cache
    if _bm25_cache is None:
        chunks = load_chunks()
        corpus_tokens = [_tokenize(c.text) for c in chunks]
        _bm25_cache = (BM25Okapi(corpus_tokens), chunks)
    return _bm25_cache


def sparse_search(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k or get_settings().retrieval_top_k
    bm25, chunks = _get_bm25()
    if not chunks:
        return []
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)[:k]
    return [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            metadata=c.metadata,
            score=float(s),
        )
        for c, s in ranked
        if s > 0
    ]
