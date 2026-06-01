# ROLE: retriever — debug payload for live retrieval traces.

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class RetrievalDebugInfo:
    subtask_query: str
    user_question: str
    fused_search_queries: list[str] = field(default_factory=list)
    title_probe_candidates: list[str] = field(default_factory=list)
    pages_fetched: list[dict] = field(default_factory=list)
    chunks_returned: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
