from unittest.mock import patch

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
    settings = Settings()
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        with patch("poe_agent.harness.provider_health.ollama_reachable", return_value=True):
            modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["ollama"] == "true"
