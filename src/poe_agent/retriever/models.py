# ROLE: retriever — data models for chunks and retrieval results.

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    score: float
