# Tests for LangGraph per-phase timing_ms.

from __future__ import annotations

from unittest.mock import patch

from poe_agent.orchestrator.graph import run_agent_graph
from poe_agent.retriever.models import RetrievedChunk


def test_run_agent_graph_returns_timing_keys():
    fake_chunk = RetrievedChunk(
        "c1",
        "Poison deals damage over time.",
        {"page_title": "Poison", "wiki_url": "https://www.poewiki.net/wiki/Poison"},
        0.8,
    )

    with (
        patch("poe_agent.orchestrator.graph.plan_subtasks", return_value=[{"action": "retrieve", "query": "poison"}]),
        patch(
            "poe_agent.orchestrator.graph.execute_subtasks",
            return_value=([fake_chunk], []),
        ),
        patch(
            "poe_agent.orchestrator.graph.synthesize_answer",
            return_value=("Poison is DoT.", [], {}),
        ),
    ):
        result = run_agent_graph("how does poison work")

    timing = result.get("timing_ms", {})
    assert "plan" in timing
    assert "retrieval" in timing
    assert "generation" in timing
    assert timing["generation"] >= 0
