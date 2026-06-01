# ROLE: retriever — heuristic gate for optional retrieval refinement.

from __future__ import annotations

from poe_agent.harness.config import get_settings
from poe_agent.retriever.models import RetrievedChunk
from poe_agent.retriever.query_fusion import extract_topic_terms


def _title_overlaps_any(page_title: str, topic_terms: list[str]) -> bool:
    import re

    title_tokens = set(re.findall(r"[a-z0-9]+", page_title.lower()))
    for term in topic_terms:
        term_tokens = set(re.findall(r"[a-z0-9]+", term.lower()))
        if term_tokens and term_tokens & title_tokens:
            return True
    return False


def retrieval_needs_refine(chunks: list[RetrievedChunk], user_question: str) -> tuple[bool, str]:
    """Return (needs_refine, reason). Heuristic only — no LLM."""
    settings = get_settings()
    if not settings.retrieval_refine_enabled:
        return False, ""

    if not chunks:
        return True, "no_chunks"

    top_score = max((c.score for c in chunks), default=0.0)
    if top_score < settings.retrieval_refine_min_score:
        return True, "low_top_score"

    terms = extract_topic_terms(user_question)
    if terms:
        titles = {str(c.metadata.get("page_title", "")) for c in chunks}
        if not any(_title_overlaps_any(t, terms) for t in titles if t):
            return True, "title_mismatch"

    return False, ""
