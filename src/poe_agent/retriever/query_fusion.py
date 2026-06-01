# ROLE: retriever — deterministic search query expansion for live wiki retrieval.

from __future__ import annotations

import re

from poe_agent.harness.config import get_settings

_STOPWORDS = frozenset(
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
        "explain",
        "tell",
        "me",
        "please",
        "path",
        "exile",
        "poe",
        "wiki",
        "game",
        "mechanic",
        "mechanics",
    }
)

_WHAT_ARE_RE = re.compile(
    r"what\s+(?:are|is)\s+(?:the\s+)?(.+?)\??\s*$",
    re.IGNORECASE,
)


def _normalize_query(text: str) -> str:
    return " ".join(text.split()).strip()


def _dedupe_queries(queries: list[str], max_count: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = _normalize_query(q)
        if not q or len(q) < 2:
            continue
        key = q.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
        if len(out) >= max_count:
            break
    return out


def extract_topic_terms(user_question: str) -> list[str]:
    """Terms used for title overlap checks and title-probe candidates."""
    q = _normalize_query(user_question)
    terms: list[str] = []

    match = _WHAT_ARE_RE.search(q)
    if match:
        phrase = match.group(1).strip(" ?.")
        if phrase:
            terms.append(phrase)
            parts = [p for p in re.split(r"[\s,]+", phrase) if p and p.lower() not in _STOPWORDS]
            if len(parts) >= 2:
                terms.append(parts[0])

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", q)
    for tok in tokens:
        low = tok.lower()
        if low in _STOPWORDS or len(tok) < 3:
            continue
        if tok[0].isupper() or low not in _STOPWORDS:
            terms.append(tok)

    # Longest meaningful phrases from consecutive non-stopword tokens
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", q) if w.lower() not in _STOPWORDS]
    if len(words) >= 2:
        terms.append(" ".join(words[:4]))

    seen: set[str] = set()
    unique: list[str] = []
    for t in terms:
        t = t.strip()
        if not t:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)
    return unique[:6]


def build_search_queries(
    user_question: str,
    subtask_query: str | None = None,
    extra_queries: list[str] | None = None,
) -> list[str]:
    """Ordered search strings: verbatim user question first, then variants."""
    settings = get_settings()
    max_q = settings.live_wiki_max_search_queries
    user_q = _normalize_query(user_question)
    sub_q = _normalize_query(subtask_query or "")

    candidates: list[str] = []
    if user_q:
        candidates.append(user_q)
    if sub_q and sub_q.casefold() != user_q.casefold():
        candidates.append(sub_q)

    for term in extract_topic_terms(user_question):
        candidates.append(term)
        if " " in term:
            first = term.split()[0]
            if first.lower() not in _STOPWORDS:
                candidates.append(first)

    if extra_queries:
        candidates.extend(extra_queries)

    return _dedupe_queries(candidates, max_q)


def title_probe_candidates(user_question: str, max_candidates: int = 2) -> list[str]:
    """Page titles to try via direct parse API (high precision)."""
    terms = extract_topic_terms(user_question)
    probes: list[str] = []
    for term in terms:
        if " " in term:
            probes.append(term)
            probes.append(term.split()[0])
        else:
            probes.append(term)
    seen: set[str] = set()
    out: list[str] = []
    for p in probes:
        p = p.strip()
        if not p or len(p) < 3:
            continue
        key = p.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= max_candidates:
            break
    return out
