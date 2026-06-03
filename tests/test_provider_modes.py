from unittest.mock import patch

import pytest
from fastapi import HTTPException

from poe_agent.harness.api.settings_routes import set_provider
from poe_agent.harness.api.schemas import ProviderSettingsRequest
from poe_agent.harness.config import Settings, list_available_provider_modes


def test_claude_gpt4_unavailable_without_keys():
    settings = Settings(anthropic_api_key="", openai_api_key="")
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        with patch("poe_agent.harness.provider_health.ollama_reachable", return_value=False):
            modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["stub"] == "true"
    assert modes["claude"] == "false"
    assert modes["gpt4"] == "false"
    assert modes["ollama"] == "false"


def test_claude_available_with_anthropic_key():
    settings = Settings(anthropic_api_key="sk-ant-test", openai_api_key="")
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        with patch("poe_agent.harness.provider_health.ollama_reachable", return_value=False):
            modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["claude"] == "true"
    assert modes["gpt4"] == "false"


def test_ollama_available_when_reachable():
    settings = Settings(enable_ollama=True)
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        with patch("poe_agent.harness.provider_health.ollama_reachable", return_value=True):
            modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["ollama"] == "true"


def test_ollama_hidden_when_disabled():
    settings = Settings(enable_ollama=False)
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        with patch("poe_agent.harness.provider_health.ollama_reachable", return_value=True):
            ids = [m["id"] for m in list_available_provider_modes()]
    assert "ollama" not in ids
    assert "stub" in ids
    assert "claude" in ids


def test_set_provider_rejects_ollama_when_disabled():
    settings = Settings(enable_ollama=False)
    with patch("poe_agent.harness.api.settings_routes.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            set_provider(ProviderSettingsRequest(mode="ollama"))
    assert exc_info.value.status_code == 400
    assert "not available" in exc_info.value.detail.lower()
