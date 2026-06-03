# Tests for retrieval refinement gate.

from __future__ import annotations

from poe_agent.retriever.gate import retrieval_needs_refine


def test_gate_disabled_by_default(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_REFINE_ENABLED", "false")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()
    needs, _ = retrieval_needs_refine([], "What are Pantheon powers?")
    assert needs is False
    get_settings.cache_clear()


def test_gate_no_chunks(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_REFINE_ENABLED", "true")
    from poe_agent.harness.config import get_settings

    get_settings.cache_clear()
    needs, reason = retrieval_needs_refine([], "test")
    assert needs is True
    assert reason == "no_chunks"
    get_settings.cache_clear()
