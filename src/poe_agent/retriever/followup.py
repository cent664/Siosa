# ROLE: retriever — cheap follow-up rewrite + topic-continuity gates (no extra LLM).

from __future__ import annotations

import re

_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "what",
        "which",
        "who",
        "how",
        "why",
        "when",
        "where",
        "does",
        "do",
        "did",
        "can",
        "could",
        "should",
        "would",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "with",
        "from",
        "about",
        "tell",
        "me",
        "please",
        "path",
        "exile",
        "poe",
        "wiki",
        "get",
        "more",
        "all",
        "any",
        "some",
    }
)

# Deixis / vague references — only these (not “how do I …”, which matches new topics too).
_DEIXIS_MARKERS = re.compile(
    r"\b("
    r"them|those|these|they|"
    r"\bit\b|\bthat\b|"
    r"does\s+that|what\s+about|"
    r"any\s+of\s+them|which\s+ones|"
    r"list\s+all|list\s+them|all\s+of\s+them"
    r")\b",
    re.IGNORECASE,
)

_ENUMERATE_MARKERS = re.compile(
    r"\b("
    r"list\s+all|list\s+them|list\s+the|all\s+of\s+them|"
    r"name\s+(?:all|them|every)|every\s+one|which\s+ones|"
    r"the\s+gods|the\s+powers|major\s+and\s+minor|all\s+gods"
    r")\b",
    re.IGNORECASE,
)


def _tokens(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(t) > 2 and t not in _STOP
    }


def topic_overlap_score(
    question: str,
    prior_titles: list[str] | None = None,
    prior_questions: list[str] | None = None,
) -> float:
    """Fraction of current-question tokens that also appear in prior titles/questions."""
    qt = _tokens(question)
    if not qt:
        return 0.0
    prior: set[str] = set()
    for t in prior_titles or []:
        prior |= _tokens(t)
    for pq in (prior_questions or [])[-3:]:
        prior |= _tokens(pq)
    if not prior:
        return 0.0
    return len(qt & prior) / len(qt)


def looks_like_followup(question: str) -> bool:
    """True for deictic / vague follow-ups (not every short or 'how do I' question)."""
    return bool(_DEIXIS_MARKERS.search(question.strip()))


def looks_like_enumerate(question: str) -> bool:
    """True when the user wants a full list — prefer table links + more hops."""
    return bool(_ENUMERATE_MARKERS.search(question.strip()))


def is_topic_continuation(
    question: str,
    prior_titles: list[str] | None = None,
    *,
    prior_questions: list[str] | None = None,
    min_overlap: float = 0.2,
) -> bool:
    """
    Gate prior-page / link-expand continuity.

    New topics (e.g. poison after Pantheon) must get a fresh wiki search.
    Follow-ups with deixis or clear lexical overlap keep prior pages.
    """
    titles = [t.strip() for t in (prior_titles or []) if t and t.strip()]
    prior_qs = [q for q in (prior_questions or []) if q and str(q).strip()]
    if not titles and not prior_qs:
        return False

    q = question.strip()
    if looks_like_enumerate(q) or looks_like_followup(q):
        return True

    return topic_overlap_score(q, titles, prior_qs) >= min_overlap


def rewrite_followup_question(question: str, prior_titles: list[str] | None) -> str:
    """
    If the user says “list all of them” after Pantheon, search “list all of them Pantheon”.
    Only when the ask continues the prior topic.
    """
    titles = [t.strip() for t in (prior_titles or []) if t and t.strip()]
    q = question.strip()
    if not titles or not is_topic_continuation(q, titles):
        return q
    if not looks_like_followup(q) and not looks_like_enumerate(q):
        return q

    q_fold = q.casefold()
    if any(t.casefold() in q_fold for t in titles):
        return q

    return f"{q} {titles[0]}".strip()
