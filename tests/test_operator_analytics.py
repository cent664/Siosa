# Tests for operator analytics gating, logging, and private dashboard.

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from poe_agent.harness.api.app import app
from poe_agent.harness.config import Settings, get_settings, operator_analytics_active
from poe_agent.harness.operator_analytics import (
    fetch_recent_events,
    fetch_summary,
    log_event,
    log_visit_once_per_day,
)


def test_operator_analytics_allowed_under_production_when_enabled():
    settings = Settings(
        deployment_profile="production",
        operator_analytics_enabled=True,
    )
    assert operator_analytics_active(settings) is True


def test_operator_analytics_off_when_disabled():
    settings = Settings(
        deployment_profile="production",
        operator_analytics_enabled=False,
    )
    assert operator_analytics_active(settings) is False


def test_operator_analytics_logs_ask_when_enabled(tmp_path: Path):
    settings = Settings(
        deployment_profile="",
        operator_analytics_enabled=True,
        poe_data_dir=tmp_path,
    )
    assert operator_analytics_active(settings) is True
    log_event(path="/query", action="ask", client_ip="1.2.3.4", country="US", settings=settings)
    db = tmp_path / "operator_analytics.sqlite"
    assert db.is_file()
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute("SELECT action, country, ip_hash FROM events").fetchone()
    assert row[0] == "ask"
    assert row[1] == "US"
    assert len(row[2]) == 64


def test_operator_analytics_noop_when_disabled(tmp_path: Path):
    settings = Settings(
        operator_analytics_enabled=False,
        poe_data_dir=tmp_path,
    )
    log_event(path="/query", action="ask", client_ip="1.2.3.4", settings=settings)
    log_visit_once_per_day(client_ip="1.2.3.4", settings=settings)
    assert not (tmp_path / "operator_analytics.sqlite").exists()


def test_visit_once_per_day_dedupes(tmp_path: Path):
    settings = Settings(
        operator_analytics_enabled=True,
        poe_data_dir=tmp_path,
    )
    assert log_visit_once_per_day(client_ip="1.1.1.1", country="CA", settings=settings) is True
    assert log_visit_once_per_day(client_ip="1.1.1.1", country="CA", settings=settings) is False
    assert log_visit_once_per_day(client_ip="2.2.2.2", country="US", settings=settings) is True
    rows = fetch_recent_events(limit=10, settings=settings)
    assert len(rows) == 2
    assert all(r["action"] == "visit" for r in rows)


def test_fetch_summary_counts_unique_and_asks(tmp_path: Path):
    settings = Settings(
        operator_analytics_enabled=True,
        poe_data_dir=tmp_path,
    )
    log_visit_once_per_day(client_ip="1.1.1.1", settings=settings)
    log_visit_once_per_day(client_ip="2.2.2.2", settings=settings)
    log_event(path="/query", action="ask", client_ip="1.1.1.1", settings=settings)
    log_event(path="/query", action="ask", client_ip="1.1.1.1", settings=settings)
    summary = fetch_summary(settings=settings)
    assert summary["unique_visitors"] == 2
    assert summary["total_visits"] == 2
    assert summary["total_asks"] == 2


def test_fetch_recent_events_filters_to_visit_and_ask(tmp_path: Path):
    settings = Settings(
        operator_analytics_enabled=True,
        poe_data_dir=tmp_path,
    )
    log_event(path="/assets/x.js", action="GET /assets/x.js", client_ip="1.1.1.1", settings=settings)
    log_event(path="/query", action="ask", client_ip="1.1.1.1", settings=settings)
    rows = fetch_recent_events(limit=10, settings=settings)
    assert [r["action"] for r in rows] == ["ask"]


def test_dashboard_404_when_analytics_inactive(tmp_path: Path):
    settings = Settings(
        deployment_profile="production",
        operator_analytics_enabled=False,
        operator_dashboard_key="secret-key",
        poe_data_dir=tmp_path,
    )
    with patch("poe_agent.harness.api.app.get_settings", return_value=settings):
        client = TestClient(app)
        resp = client.get("/operator/analytics", params={"key": "secret-key"})
    assert resp.status_code == 404


def test_dashboard_ok_under_production_when_enabled(tmp_path: Path):
    settings = Settings(
        deployment_profile="production",
        operator_analytics_enabled=True,
        operator_dashboard_key="secret-key",
        poe_data_dir=tmp_path,
    )
    log_event(path="/query", action="ask", client_ip="9.9.9.9", country="CA", settings=settings)
    with patch("poe_agent.harness.api.app.get_settings", return_value=settings):
        client = TestClient(app)
        resp = client.get("/operator/analytics", params={"key": "secret-key"})
    assert resp.status_code == 200
    assert "Unique visitors" in resp.text
    assert "ask" in resp.text
    assert "CA" in resp.text
    get_settings.cache_clear()


def test_dashboard_401_wrong_or_missing_key(tmp_path: Path):
    settings = Settings(
        deployment_profile="",
        operator_analytics_enabled=True,
        operator_dashboard_key="secret-key",
        poe_data_dir=tmp_path,
    )
    with patch("poe_agent.harness.api.app.get_settings", return_value=settings):
        client = TestClient(app)
        assert client.get("/operator/analytics").status_code == 401
        assert client.get("/operator/analytics", params={"key": "wrong"}).status_code == 401


def test_dashboard_401_when_key_unset(tmp_path: Path):
    settings = Settings(
        deployment_profile="",
        operator_analytics_enabled=True,
        operator_dashboard_key="",
        poe_data_dir=tmp_path,
    )
    with patch("poe_agent.harness.api.app.get_settings", return_value=settings):
        client = TestClient(app)
        resp = client.get("/operator/analytics", params={"key": "anything"})
    assert resp.status_code == 401
