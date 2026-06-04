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
        "difference",
        "differences",
        "between",
        "compare",
        "comparison",
        "versus",
        "count",
        "as",
    }
)

_WHAT_ARE_RE = re.compile(
    r"what\s+(?:are|is)\s+(?:the\s+)?(.+?)\??\s*$",
    re.IGNORECASE,
)
_BETWEEN_AND_RE = re.compile(
    r"(?:what\s+is\s+)?(?:the\s+)?(?:difference|differences|comparison)\s+between\s+(.+?)\s+and\s+(.+?)\??\s*$",
    re.IGNORECASE,
)
_VS_RE = re.compile(r"(.+?)\s+vs\.?\s+(.+?)\??\s*$", re.IGNORECASE)
_COUNT_AS_RE = re.compile(
    r"does\s+(.+?)\s+count\s+as\s+(.+?)\??\s*$",
    re.IGNORECASE,
)
_COMPARE_RE = re.compile(r"compare\s+(.+?)\s+(?:to|with|and)\s+(.+?)\??\s*$", re.IGNORECASE)

_MAX_ENTITY_PHRASE_WORDS = 5
_MAX_SEARCH_TERM_CHARS = 48


def _normalize_query(text: str) -> str:
    return " ".join(text.split()).strip()


def _clean_entity(text: str) -> str:
    s = text.strip(" ?.,;:\"'")
    s = re.sub(r"^(?:the|a|an)\s+", "", s, flags=re.IGNORECASE)
    return s.strip()


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


def _is_reasonable_search_term(term: str) -> bool:
    term = term.strip()
    if len(term) < 2 or len(term) > _MAX_SEARCH_TERM_CHARS:
        return False
    if len(term.split()) > _MAX_ENTITY_PHRASE_WORDS:
        return False
    return True


def extract_mechanic_entities(user_question: str) -> list[str]:
    """Mechanic/skill/page names from compare and yes/no patterns."""
    q = _normalize_query(user_question)
    raw_pairs: list[tuple[str, str]] = []

    for pattern in (_BETWEEN_AND_RE, _VS_RE, _COUNT_AS_RE, _COMPARE_RE):
        match = pattern.search(q)
        if match:
            raw_pairs.append((match.group(1), match.group(2)))
            break

    entities: list[str] = []
    for left, right in raw_pairs:
        for part in (left, right):
            cleaned = _clean_entity(part)
            if cleaned and _is_reasonable_search_term(cleaned):
                entities.append(cleaned)

    seen: set[str] = set()
    unique: list[str] = []
    for ent in entities:
        key = ent.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(ent)
    return unique[:4]


def extract_topic_terms(user_question: str) -> list[str]:
    """Terms used for title overlap checks and title-probe candidates."""
    q = _normalize_query(user_question)
    terms: list[str] = []

    for ent in extract_mechanic_entities(user_question):
        terms.append(ent)

    match = _WHAT_ARE_RE.search(q)
    if match:
        phrase = match.group(1).strip(" ?.")
        if phrase and _is_reasonable_search_term(phrase):
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

    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]*", q) if w.lower() not in _STOPWORDS]
    if len(words) >= 2 and len(words) <= _MAX_ENTITY_PHRASE_WORDS:
        phrase = " ".join(words[:4])
        if _is_reasonable_search_term(phrase):
            terms.append(phrase)

    seen: set[str] = set()
    unique: list[str] = []
    for t in terms:
        t = t.strip()
        if not t or not _is_reasonable_search_term(t):
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(t)
    return unique[:8]


def retrieval_focus_terms(user_question: str) -> list[str]:
    """Combined terms for title relevance scoring and overlap filters."""
    seen: set[str] = set()
    out: list[str] = []
    for t in extract_mechanic_entities(user_question) + extract_topic_terms(user_question):
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def build_search_queries(
    user_question: str,
    subtask_query: str | None = None,
    extra_queries: list[str] | None = None,
) -> list[str]:
    """Ordered search strings: short mechanic queries first, full question last."""
    settings = get_settings()
    max_q = settings.live_wiki_max_search_queries
    user_q = _normalize_query(user_question)
    sub_q = _normalize_query(subtask_query or "")

    short: list[str] = []
    for ent in extract_mechanic_entities(user_question):
        short.append(ent)

    if sub_q and sub_q.casefold() != user_q.casefold() and _is_reasonable_search_term(sub_q):
        short.append(sub_q)

    for term in extract_topic_terms(user_question):
        if term.casefold() in {e.casefold() for e in extract_mechanic_entities(user_question)}:
            continue
        short.append(term)
        if " " in term:
            first = term.split()[0]
            if first.lower() not in _STOPWORDS and len(first) >= 3:
                short.append(first)

    if extra_queries:
        short.extend(extra_queries)

    reserved = 1 if user_q else 0
    short_slot = max(1, max_q - reserved)
    ordered = _dedupe_queries(short, short_slot)
    if user_q:
        ordered = _dedupe_queries(ordered + [user_q], max_q)
    return ordered


def title_probe_candidates(user_question: str, max_candidates: int | None = None) -> list[str]:
    """Page titles to try via direct parse API (high precision)."""
    settings = get_settings()
    max_c = max_candidates if max_candidates is not None else settings.live_wiki_max_title_probes

    probes: list[str] = []
    for ent in extract_mechanic_entities(user_question):
        probes.append(ent)

    for term in extract_topic_terms(user_question):
        if " " in term:
            probes.append(term)
            first = term.split()[0]
            if first[0].isupper() and first.lower() not in _STOPWORDS:
                probes.append(first)
        elif term[0].isupper() and len(term) >= 3:
            probes.append(term)

    seen: set[str] = set()
    out: list[str] = []
    for p in probes:
        p = p.strip()
        if not p or not _is_reasonable_search_term(p):
            continue
        key = p.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= max_c:
            break
    return out
