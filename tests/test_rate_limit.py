# Tests for UTC daily Ask rate limiting.

from __future__ import annotations

from pathlib import Path

from poe_agent.harness.config import Settings
from poe_agent.harness.rate_limit import check_and_increment_ask


def test_rate_limit_disabled_always_allows(tmp_path: Path):
    settings = Settings(
        rate_limit_enabled=False,
        rate_limit_asks_per_day=2,
        poe_data_dir=tmp_path,
    )
    for _ in range(5):
        d = check_and_increment_ask("1.2.3.4", settings)
        assert d.allowed is True


def test_rate_limit_enforced_per_day(tmp_path: Path):
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_asks_per_day=2,
        poe_data_dir=tmp_path,
    )
    assert check_and_increment_ask("9.9.9.9", settings).allowed is True
    assert check_and_increment_ask("9.9.9.9", settings).remaining == 0
    blocked = check_and_increment_ask("9.9.9.9", settings)
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds >= 1
    # Different IP still allowed
    assert check_and_increment_ask("8.8.8.8", settings).allowed is True
