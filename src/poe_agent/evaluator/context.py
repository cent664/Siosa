# ROLE: evaluator — shared excerpt formatting for generator and judges.

from __future__ import annotations

from poe_agent.retriever.models import RetrievedChunk

EVIDENCE_CHARS_PER_CHUNK = 1200
JUDGE_CONTEXT_MAX_CHARS = 6000


def format_evidence_context(
    chunks: list[RetrievedChunk],
    *,
    max_chars_per_chunk: int = EVIDENCE_CHARS_PER_CHUNK,
) -> str:
    """Same shape as the answer LLM context: numbered excerpts with title and URL."""
    if not chunks:
        return "(no chunks retrieved)"
    parts: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        title = ch.metadata.get("page_title", "Unknown")
        url = ch.metadata.get("wiki_url", "")
        parts.append(f"[{i}] {title} ({url})\n{ch.text[:max_chars_per_chunk]}")
    return "\n\n".join(parts)


def truncate_for_judge(context: str, max_chars: int = JUDGE_CONTEXT_MAX_CHARS) -> str:
    if len(context) <= max_chars:
        return context
    return context[:max_chars] + "\n…(truncated)"
