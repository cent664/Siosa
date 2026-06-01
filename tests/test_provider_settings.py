# Tests for runtime provider override and settings API.

import pytest
from fastapi.testclient import TestClient

from poe_agent.harness.api.app import app
from poe_agent.harness.config import (
    get_effective_judge_provider,
    get_effective_provider_mode,
    get_settings,
    set_runtime_judge_provider,
    set_runtime_provider_mode,
)


@pytest.fixture(autouse=True)
def clear_runtime_provider():
    set_runtime_provider_mode(None)
    set_runtime_judge_provider(None)
    get_settings.cache_clear()
    yield
    set_runtime_provider_mode(None)
    set_runtime_judge_provider(None)
    get_settings.cache_clear()


def test_runtime_override():
    get_settings.cache_clear()
    set_runtime_provider_mode("stub")
    assert get_effective_provider_mode() == "stub"


def test_invalid_runtime_mode():
    with pytest.raises(ValueError):
        set_runtime_provider_mode("invalid")


def test_get_provider_endpoint():
    client = TestClient(app)
    resp = client.get("/settings/provider")
    assert resp.status_code == 200
    data = resp.json()
    assert "mode" in data
    assert "source" in data
    assert "available_modes" in data
    assert any(m["id"] == "stub" for m in data["available_modes"])


def test_set_provider_invalid_via_api():
    client = TestClient(app)
    resp = client.post("/settings/provider", json={"mode": "bedrock"})
    assert resp.status_code == 422


def test_set_gpt4_without_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    client = TestClient(app)
    resp = client.post("/settings/provider", json={"mode": "gpt4"})
    assert resp.status_code == 400
    get_settings.cache_clear()


def test_set_claude_aligns_judge_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    get_settings.cache_clear()
    client = TestClient(app)
    resp = client.post("/settings/provider", json={"mode": "claude"})
    assert resp.status_code == 200
    assert resp.json()["judge_provider"] == "claude"
    assert get_effective_judge_provider() == "claude"
    get_settings.cache_clear()
