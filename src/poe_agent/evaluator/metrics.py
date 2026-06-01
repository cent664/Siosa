# ROLE: evaluator — retrieval precision/recall and latency helpers.

from __future__ import annotations

from poe_agent.retriever.models import RetrievedChunk


def retrieval_precision(retrieved_titles: list[str], expected_pages: list[str]) -> float:
    if not retrieved_titles:
        return 0.0
    expected = {p.lower() for p in expected_pages}
    hits = sum(1 for t in retrieved_titles if t.lower() in expected)
    return hits / len(retrieved_titles)


def retrieval_recall(retrieved_titles: list[str], expected_pages: list[str]) -> float:
    if not expected_pages:
        return 1.0
    expected = {p.lower() for p in expected_pages}
    hits = sum(1 for p in expected if any(p in t.lower() for t in retrieved_titles))
    return hits / len(expected)


def titles_from_chunks(chunks: list[RetrievedChunk]) -> list[str]:
    return [str(c.metadata.get("page_title", "")) for c in chunks]
