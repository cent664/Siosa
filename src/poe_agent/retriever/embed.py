# ROLE: retriever — embed chunks and persist to ChromaDB.

from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from poe_agent.harness.config import get_settings
from poe_agent.harness.providers import get_embedding_provider
from poe_agent.retriever.ingest import load_chunks

COLLECTION_NAME = "poe_wiki_chunks"


def get_chroma_collection():
    settings = get_settings()
    settings.poe_chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(settings.poe_chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index() -> int:
    chunks = load_chunks()
    if not chunks:
        raise FileNotFoundError("No chunks.jsonl — run ingest first.")

    collection = get_chroma_collection()
    # Reset collection
    try:
        client = chromadb.PersistentClient(path=str(get_settings().poe_chroma_dir))
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = get_chroma_collection()

    embedder = get_embedding_provider()
    batch_size = 32
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embedder.embed([c.text for c in batch])
        collection.add(
            ids=[c.chunk_id for c in batch],
            documents=[c.text for c in batch],
            embeddings=vectors,
            metadatas=[c.metadata for c in batch],
        )
    return len(chunks)
