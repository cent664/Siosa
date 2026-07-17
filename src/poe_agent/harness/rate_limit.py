# ROLE: harness — UTC daily Ask rate limits (per client IP).

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    limit: int
    day_utc: str
    retry_after_seconds: int = 0


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _seconds_until_next_utc_day() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta

    tomorrow = tomorrow + timedelta(days=1)
    return max(1, int((tomorrow - now).total_seconds()))


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ask_counts (
            client_key TEXT NOT NULL,
            day_utc TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (client_key, day_utc)
        )
        """
    )
    conn.commit()
    return conn


def check_and_increment_ask(
    client_key: str,
    settings: Settings | None = None,
) -> RateLimitDecision:
    """If rate limiting disabled, always allow. Otherwise increment and enforce daily cap."""
    s = settings or get_settings()
    day = _utc_day()
    limit = max(1, int(s.rate_limit_asks_per_day))

    if not s.rate_limit_enabled:
        return RateLimitDecision(allowed=True, remaining=limit, limit=limit, day_utc=day)

    key = (client_key or "unknown").strip() or "unknown"
    with _connect(s.rate_limit_db_path) as conn:
        row = conn.execute(
            "SELECT count FROM ask_counts WHERE client_key = ? AND day_utc = ?",
            (key, day),
        ).fetchone()
        current = int(row[0]) if row else 0
        if current >= limit:
            return RateLimitDecision(
                allowed=False,
                remaining=0,
                limit=limit,
                day_utc=day,
                retry_after_seconds=_seconds_until_next_utc_day(),
            )
        new_count = current + 1
        conn.execute(
            """
            INSERT INTO ask_counts (client_key, day_utc, count) VALUES (?, ?, ?)
            ON CONFLICT(client_key, day_utc) DO UPDATE SET count = excluded.count
            """,
            (key, day, new_count),
        )
        conn.commit()
        return RateLimitDecision(
            allowed=True,
            remaining=max(0, limit - new_count),
            limit=limit,
            day_utc=day,
        )
