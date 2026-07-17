from unittest.mock import patch

import pytest
from fastapi import HTTPException

from poe_agent.harness.api.settings_routes import set_provider
from poe_agent.harness.api.schemas import ProviderSettingsRequest
from poe_agent.harness.config import Settings, deployment_hint, list_available_provider_modes


def test_claude_gpt4_unavailable_without_keys():
    settings = Settings(anthropic_api_key="", openai_api_key="")
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["claude"] == "false"
    assert modes["gpt4"] == "false"
    assert "stub" not in modes
    assert "ollama" not in modes


def test_claude_available_with_anthropic_key():
    settings = Settings(anthropic_api_key="sk-ant-test", openai_api_key="")
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        modes = {m["id"]: m["available"] for m in list_available_provider_modes()}
    assert modes["claude"] == "true"
    assert modes["gpt4"] == "false"


def test_provider_modes_claude_gpt4_only():
    settings = Settings(anthropic_api_key="sk-ant-test", openai_api_key="sk-test")
    with patch("poe_agent.harness.config.get_settings", return_value=settings):
        ids = [m["id"] for m in list_available_provider_modes()]
    assert ids == ["claude", "gpt4"]


def test_deployment_profile_applies_production_defaults():
    settings = Settings(
        deployment_profile="production",
        anthropic_api_key="sk-ant-test",
        operator_analytics_enabled=True,
    )
    assert settings.inline_eval is False
    assert settings.operator_analytics_enabled is False
    assert settings.transcribe_provider == "openai"
    assert settings.judge_provider == "claude"
    assert settings.poe_provider_mode == "claude"


def test_deployment_profile_normalizes_invalid_provider():
    settings = Settings(
        deployment_profile="production",
        poe_provider_mode="stub",
        anthropic_api_key="",
    )
    assert settings.inline_eval is False
    assert settings.poe_provider_mode == "claude"


def test_deployment_hint_when_inline_eval_on_deployed_host():
    settings = Settings(
        inline_eval=True,
        poe_api_host="0.0.0.0",
        poe_api_base_url="https://example.railway.app",
    )
    hint = deployment_hint(settings)
    assert "DEPLOYMENT_PROFILE=production" in hint


def test_deployment_hint_empty_on_localhost():
    settings = Settings(inline_eval=True, poe_api_host="127.0.0.1")
    assert deployment_hint(settings) == ""


def test_deployment_hint_empty_when_production_profile():
    settings = Settings(deployment_profile="production")
    assert deployment_hint(settings) == ""


def test_set_provider_rejects_claude_without_key():
    settings = Settings(anthropic_api_key="")
    with patch("poe_agent.harness.api.settings_routes.get_settings", return_value=settings):
        with pytest.raises(HTTPException) as exc_info:
            set_provider(ProviderSettingsRequest(mode="claude"))
    assert exc_info.value.status_code == 400
