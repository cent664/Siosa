# ROLE: planner — LLM-generated short search queries for retrieval refinement.

from __future__ import annotations

import json
import re

from poe_agent.harness.providers import get_llm_provider
from poe_agent.retriever.models import RetrievedChunk

REFINE_SYSTEM = """You improve Path of Exile 1 wiki search queries after weak retrieval.
Return ONLY valid JSON: {"queries": ["short search 1", "short search 2"]}
Rules:
- 1-2 queries only, each 1-4 words (mechanic or wiki page title words)
- Do NOT repeat the user's full question verbatim
- Do NOT add generic phrases like "Path of Exile mechanics" or "PoE wiki"
- Target the core topic from the user question and avoid pages already retrieved"""


def refine_search_queries(
    user_question: str,
    chunks: list[RetrievedChunk],
) -> list[str]:
    titles = [str(c.metadata.get("page_title", "")) for c in chunks[:8]]
    scores = [c.score for c in chunks[:8]]
    summary = "\n".join(f"- {t} (score {s:.2f})" for t, s in zip(titles, scores) if t)

    try:
        llm = get_llm_provider()
        raw, _ = llm.generate(
            REFINE_SYSTEM,
            f"User question: {user_question}\n\nRetrieved pages:\n{summary or '(none)'}\n\nReturn JSON only.",
        )
    except Exception:
        from poe_agent.retriever.query_fusion import extract_topic_terms

        return extract_topic_terms(user_question)[:2]
    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            queries = data.get("queries", [])
            if isinstance(queries, list):
                return [str(q).strip() for q in queries if str(q).strip()][:2]
    except json.JSONDecodeError:
        pass

    from poe_agent.retriever.query_fusion import extract_topic_terms

    return extract_topic_terms(user_question)[:2]
