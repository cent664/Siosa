# ROLE: retriever — cheap follow-up query rewrite without an extra LLM call.

from __future__ import annotations

import re

# Pronouns / vague asks that usually need the prior topic name baked into search.
_FOLLOWUP_MARKERS = re.compile(
    r"\b("
    r"them|those|these|they|it|that|"
    r"list\s+all|list\s+them|all\s+of\s+them|"
    r"unlock|how\s+do\s+i|does\s+that|what\s+about|"
    r"any\s+of\s+them|which\s+ones|the\s+gods|the\s+powers"
    r")\b",
    re.IGNORECASE,
)

# “List / name every …” — expand more links from content tables on the prior index page.
_ENUMERATE_MARKERS = re.compile(
    r"\b("
    r"list\s+all|list\s+them|list\s+the|all\s+of\s+them|"
    r"name\s+(?:all|them|every)|every\s+one|which\s+ones|"
    r"the\s+gods|the\s+powers|major\s+and\s+minor|all\s+gods"
    r")\b",
    re.IGNORECASE,
)


def looks_like_followup(question: str) -> bool:
    q = question.strip()
    if len(q) < 8:
        return True
    return bool(_FOLLOWUP_MARKERS.search(q))


def looks_like_enumerate(question: str) -> bool:
    """True when the user wants a full list — prefer table links + more hops."""
    return bool(_ENUMERATE_MARKERS.search(question.strip()))


def rewrite_followup_question(question: str, prior_titles: list[str] | None) -> str:
    """
    If the user says “list all of them” after Pantheon, search “list all of them Pantheon”.
    Rule of thumb: resolve deixis with prior citation titles before hitting the wiki.
    """
    titles = [t.strip() for t in (prior_titles or []) if t and t.strip()]
    if not titles or not looks_like_followup(question):
        return question.strip()

    q = question.strip()
    q_fold = q.casefold()
    if any(t.casefold() in q_fold for t in titles):
        return q

    # Prefer the strongest prior topic (first citation titles are usually the index page).
    anchor = titles[0]
    return f"{q} {anchor}".strip()
