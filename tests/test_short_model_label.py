# Tests for provider dropdown short model labels.

from __future__ import annotations

from poe_agent.harness.config import short_model_label


def test_short_model_label_claude_sonnet():
    assert short_model_label("claude-sonnet-4-6") == "Sonnet 4.6"


def test_short_model_label_gpt():
    assert short_model_label("gpt-4o") == "GPT-4o"


def test_short_model_label_empty():
    assert short_model_label("") == "Claude"


def test_list_available_provider_modes_uses_model_names(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    from poe_agent.harness.config import get_settings, list_available_provider_modes

    get_settings.cache_clear()
    modes = {m["id"]: m["label"] for m in list_available_provider_modes()}
    assert "stub" not in modes
    assert modes["claude"] == "Sonnet 4.6"
    assert modes["gpt4"] == "GPT-4o"
    get_settings.cache_clear()
