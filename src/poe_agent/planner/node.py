# ROLE: planner — produces a JSON plan of subtasks for the executor.

from __future__ import annotations

import json
import re

from poe_agent.harness.config import get_settings
from poe_agent.harness.providers import get_llm_provider

PLANNER_SYSTEM = """You plan wiki lookups for Path of Exile 1 mechanic questions.
Return ONLY valid JSON: {"subtasks": [{"action": "retrieve", "query": "..."}, ...]}
Rules:
- First retrieve subtask MUST use the EXACT user question verbatim (copy it unchanged)
- Add 0-3 MORE retrieve subtasks with SHORT wiki search strings (1-4 words: mechanic or page name)
- Do NOT use generic suffixes ("Path of Exile mechanics", "PoE wiki", "game mechanics")
- Example compare: ignite vs poison -> exact question, then "ignite", then "poison"
- End with optional {"action": "synthesize", "query": "..."} (executor ignores synthesize action)"""


def _ensure_verbatim_first(question: str, subtasks: list[dict]) -> list[dict]:
    """Prepend exact user question if planner omitted it."""
    retrieve_tasks = [t for t in subtasks if t.get("action", "retrieve") != "synthesize"]
    others = [t for t in subtasks if t.get("action") == "synthesize"]
    q_norm = question.strip().casefold()
    has_verbatim = any(
        t.get("action", "retrieve") != "synthesize"
        and str(t.get("query", "")).strip().casefold() == q_norm
        for t in retrieve_tasks
    )
    if not has_verbatim:
        retrieve_tasks.insert(0, {"action": "retrieve", "query": question})
    max_r = get_settings().planner_max_retrieve_subtasks
    retrieve_tasks = retrieve_tasks[:max_r]
    return retrieve_tasks + others


def plan_subtasks(
    question: str,
    history: list[dict[str, str]] | None = None,
    summary: str = "",
) -> list[dict]:
    """LLM JSON plan with heuristic fallback on parse/API failure."""
    from poe_agent.harness.session_memory import format_generation_context, history_search_hints

    context = format_generation_context(summary or "", history or [])
    hints = history_search_hints(history or [])
    hint_line = ""
    if hints:
        hint_line = "Known topics from prior turns (use as short retrieve queries if relevant): " + ", ".join(
            hints
        )
    user_parts = []
    if context:
        user_parts.append(f"Prior conversation:\n{context}")
    if hint_line:
        user_parts.append(hint_line)
    user_parts.append(f"Question: {question}\nReturn JSON plan only.")
    user_msg = "\n\n".join(user_parts)
    try:
        llm = get_llm_provider()
        raw, _ = llm.generate(PLANNER_SYSTEM, user_msg)
    except Exception:
        return _heuristic_plan(question, hints=hints)
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            subtasks = data.get("subtasks", [])
            if subtasks:
                return _ensure_verbatim_first(question, subtasks)
    except json.JSONDecodeError:
        pass
    return _heuristic_plan(question, hints=hints)


def _heuristic_plan(question: str, hints: list[str] | None = None) -> list[dict]:
    q = question.lower()
    subtasks: list[dict] = [{"action": "retrieve", "query": question}]

    between = re.search(
        r"(?:difference|differences|comparison)\s+between\s+(.+?)\s+and\s+(.+?)\??\s*$",
        question,
        re.IGNORECASE,
    )
    count_as = re.search(
        r"does\s+(.+?)\s+count\s+as\s+(.+?)\??\s*$",
        question,
        re.IGNORECASE,
    )
    if between:
        subtasks = [
            {"action": "retrieve", "query": question},
            {"action": "retrieve", "query": between.group(1).strip(" ?.")},
            {"action": "retrieve", "query": between.group(2).strip(" ?.")},
        ]
    elif count_as:
        subtasks = [
            {"action": "retrieve", "query": question},
            {"action": "retrieve", "query": count_as.group(1).strip(" ?.")},
            {"action": "retrieve", "query": count_as.group(2).strip(" ?.")},
        ]
    elif " vs " in q or " versus " in q or "compare" in q:
        parts = re.split(r"\s+vs\.?\s+|\s+versus\s+|compare\s+", q, maxsplit=1)
        if len(parts) == 2:
            subtasks = [
                {"action": "retrieve", "query": question},
                {"action": "retrieve", "query": parts[0].strip()},
                {"action": "retrieve", "query": parts[1].strip()},
            ]
    elif "poison" in q and "ignite" in q:
        subtasks = [
            {"action": "retrieve", "query": question},
            {"action": "retrieve", "query": "poison"},
            {"action": "retrieve", "query": "ignite"},
        ]

    for hint in hints or []:
        subtasks.append({"action": "retrieve", "query": hint})

    subtasks.append({"action": "synthesize", "query": question})
    return _ensure_verbatim_first(question, subtasks)
