from fastapi.testclient import TestClient

from poe_agent.harness.api.app import app
from poe_agent.harness.config import get_settings


def test_health_includes_judge_fields():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "judge_provider" in data
    assert "judge_reachable" in data
    assert "judge_hint" in data
    assert data["judge_provider"] == get_settings().judge_provider.lower()
