# ROLE: retriever — dense vector search via ChromaDB.

from __future__ import annotations

from poe_agent.harness.config import get_settings
from poe_agent.harness.providers import get_embedding_provider
from poe_agent.retriever.embed import get_chroma_collection
from poe_agent.retriever.models import RetrievedChunk


def dense_search(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k or get_settings().retrieval_top_k
    collection = get_chroma_collection()
    if collection.count() == 0:
        return []

    embedder = get_embedding_provider()
    qvec = embedder.embed([query])[0]
    results = collection.query(query_embeddings=[qvec], n_results=min(k, collection.count()))

    out: list[RetrievedChunk] = []
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    dists = results["distances"][0]
    for cid, doc, meta, dist in zip(ids, docs, metas, dists):
        score = 1.0 / (1.0 + float(dist))
        out.append(
            RetrievedChunk(chunk_id=cid, text=doc, metadata=meta or {}, score=score)
        )
    return out
