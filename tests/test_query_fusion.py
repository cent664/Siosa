# Tests for live search query fusion.

from __future__ import annotations

from poe_agent.planner.node import _ensure_verbatim_first
from poe_agent.retriever.query_fusion import (
    build_search_queries,
    extract_mechanic_entities,
    extract_topic_terms,
    retrieval_focus_terms,
    title_probe_candidates,
)


def test_build_search_queries_short_before_verbatim():
    user = "What are Pantheon powers?"
    sub = "Pantheon powers Path of Exile mechanics"
    queries = build_search_queries(user, subtask_query=sub)
    assert user in queries
    assert queries[-1] == user
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


def test_extract_mechanic_entities_between_ignite_rf():
    q = "What is the difference between ignite and righteous fire?"
    entities = extract_mechanic_entities(q)
    assert any("ignite" in e.lower() for e in entities)
    assert any("righteous" in e.lower() for e in entities)


def test_extract_mechanic_entities_count_as():
    q = "Does righteous fire count as ignite?"
    entities = extract_mechanic_entities(q)
    assert len(entities) >= 2
    assert any("righteous" in e.lower() for e in entities)
    assert any("ignite" in e.lower() for e in entities)


def test_build_search_queries_ignite_rf_prioritizes_short():
    user = "What is the difference between ignite and righteous fire?"
    queries = build_search_queries(user, subtask_query=user)
    assert queries[-1] == user
    assert queries[0].casefold() in {"ignite", "righteous fire"}


def test_title_probe_includes_ignite_and_rf():
    q = "What is the difference between ignite and righteous fire?"
    probes = title_probe_candidates(q)
    lowered = " ".join(probes).lower()
    assert "ignite" in lowered
    assert "righteous" in lowered


def test_retrieval_focus_terms_includes_entities():
    q = "Does righteous fire count as ignite?"
    terms = retrieval_focus_terms(q)
    joined = " ".join(terms).lower()
    assert "ignite" in joined
    assert "righteous" in joined
