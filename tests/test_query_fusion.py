# Tests for live search query fusion.

from __future__ import annotations

from poe_agent.planner.node import _ensure_verbatim_first
from poe_agent.retriever.query_fusion import build_search_queries, extract_topic_terms, title_probe_candidates


def test_build_search_queries_includes_verbatim_and_subtask():
    user = "What are Pantheon powers?"
    sub = "Pantheon powers Path of Exile mechanics"
    queries = build_search_queries(user, subtask_query=sub)
    assert queries[0] == user
    assert sub in queries
    assert any("Pantheon" in q for q in queries)


def test_extract_topic_terms_pantheon():
    terms = extract_topic_terms("What are Pantheon powers?")
    assert any("pantheon" in t.lower() for t in terms)


def test_title_probe_candidates():
    probes = title_probe_candidates("What are Pantheon powers?")
    assert any("Pantheon" in p for p in probes)


def test_ensure_verbatim_first_prepends():
    plan = [{"action": "retrieve", "query": "Pantheon powers PoE"}]
    out = _ensure_verbatim_first("What are Pantheon powers?", plan)
    assert out[0]["query"] == "What are Pantheon powers?"
