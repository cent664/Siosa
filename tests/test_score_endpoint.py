# Tests for POST /score on-demand judging.

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from poe_agent.harness.api.app import app
from poe_agent.harness.api.schemas import QualityScores


def test_score_endpoint_returns_quality_scores():
    client = TestClient(app)
    fake_scores = QualityScores(
        faithfulness=4.0,
        relevance=5.0,
        notes={"faithfulness": "supported"},
    )

    with patch(
        "poe_agent.harness.api.score_service.run_inline_quality",
        return_value=(fake_scores, {"faithfulness": 120.0}),
    ):
        res = client.post(
            "/score",
            json={
                "question": "How do you unlock the scion?",
                "answer": "Complete the Freedom achievement.",
                "chunks": [
                    {
                        "page_title": "Scion",
                        "wiki_url": "https://www.poewiki.net/wiki/Scion",
                        "text": "Freedom achievement grants access to Scion.",
                    }
                ],
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert data["quality_scores"]["faithfulness"] == 4.0
    assert data["timing_ms"]["evaluation"] >= 0
