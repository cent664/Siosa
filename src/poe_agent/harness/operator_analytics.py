# ROLE: harness — optional operator analytics (local SQLite; visit + Ask events).

from __future__ import annotations

import hashlib
import html
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings, operator_analytics_active


def hash_ip(ip: str) -> str:
    return hashlib.sha256((ip or "unknown").encode("utf-8")).hexdigest()


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            path TEXT NOT NULL,
            action TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            country TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.commit()
    return conn


def log_event(
    *,
    path: str,
    action: str,
    client_ip: str,
    country: str = "",
    settings: Settings | None = None,
) -> None:
    s = settings or get_settings()
    if not operator_analytics_active(s):
        return
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect(s.operator_analytics_db_path) as conn:
        conn.execute(
            "INSERT INTO events (ts_utc, path, action, ip_hash, country) VALUES (?, ?, ?, ?, ?)",
            (
                ts,
                (path or "/")[:500],
                (action or "request")[:64],
                hash_ip(client_ip),
                (country or "")[:16],
            ),
        )
        conn.commit()


def log_visit_once_per_day(
    *,
    client_ip: str,
    country: str = "",
    settings: Settings | None = None,
) -> bool:
    """Record at most one visit per hashed IP per UTC calendar day. Returns True if inserted."""
    s = settings or get_settings()
    if not operator_analytics_active(s):
        return False
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    ip_h = hash_ip(client_ip)
    with _connect(s.operator_analytics_db_path) as conn:
        existing = conn.execute(
            """
            SELECT 1 FROM events
            WHERE action = 'visit'
              AND ip_hash = ?
              AND substr(ts_utc, 1, 10) = ?
            LIMIT 1
            """,
            (ip_h, day),
        ).fetchone()
        if existing:
            return False
        ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO events (ts_utc, path, action, ip_hash, country) VALUES (?, ?, ?, ?, ?)",
            (ts, "/", "visit", ip_h, (country or "")[:16]),
        )
        conn.commit()
    return True


def fetch_summary(settings: Settings | None = None) -> dict[str, int]:
    """Aggregate unique visitors, visits, and Asks."""
    s = settings or get_settings()
    db_path = s.operator_analytics_db_path
    empty = {
        "unique_visitors": 0,
        "total_visits": 0,
        "total_asks": 0,
        "asks_last_24h": 0,
    }
    if not db_path.is_file():
        return empty
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    with sqlite3.connect(str(db_path)) as conn:
        unique = conn.execute(
            """
            SELECT COUNT(DISTINCT ip_hash) FROM events
            WHERE action IN ('visit', 'ask')
            """
        ).fetchone()[0]
        visits = conn.execute(
            "SELECT COUNT(*) FROM events WHERE action = 'visit'"
        ).fetchone()[0]
        asks = conn.execute(
            "SELECT COUNT(*) FROM events WHERE action = 'ask'"
        ).fetchone()[0]
        asks_24h = conn.execute(
            """
            SELECT COUNT(*) FROM events
            WHERE action = 'ask' AND ts_utc >= ?
            """,
            (cutoff,),
        ).fetchone()[0]
    return {
        "unique_visitors": int(unique or 0),
        "total_visits": int(visits or 0),
        "total_asks": int(asks or 0),
        "asks_last_24h": int(asks_24h or 0),
    }


def fetch_recent_events(
    limit: int = 200,
    settings: Settings | None = None,
) -> list[dict[str, str | int]]:
    """Return newest visit/ask events first. Empty list if DB missing or no rows."""
    s = settings or get_settings()
    db_path = s.operator_analytics_db_path
    if not db_path.is_file():
        return []
    lim = max(1, min(int(limit), 500))
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT id, ts_utc, path, action, ip_hash, country
            FROM events
            WHERE action IN ('visit', 'ask')
            ORDER BY id DESC
            LIMIT ?
            """,
            (lim,),
        ).fetchall()
    return [
        {
            "id": int(r[0]),
            "ts_utc": str(r[1]),
            "path": str(r[2]),
            "action": str(r[3]),
            "ip_hash": str(r[4]),
            "country": str(r[5] or ""),
        }
        for r in rows
    ]


def render_analytics_dashboard_html(
    events: list[dict[str, str | int]],
    summary: dict[str, int] | None = None,
) -> str:
    summary = summary or {
        "unique_visitors": 0,
        "total_visits": 0,
        "total_asks": 0,
        "asks_last_24h": 0,
    }
    rows_html = []
    for ev in events:
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(str(ev['ts_utc']))}</td>"
            f"<td>{html.escape(str(ev['action']))}</td>"
            f"<td>{html.escape(str(ev['country']) or '—')}</td>"
            f"<td><code>{html.escape(str(ev['ip_hash'])[:16])}…</code></td>"
            "</tr>"
        )
    body_rows = "\n".join(rows_html) if rows_html else (
        '<tr><td colspan="4">No visits or Asks yet. Open the app or Ask a question, then refresh.</td></tr>'
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Operator analytics</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem;
           background: #0a0908; color: #e8dcc4; }}
    h1 {{ font-size: 1.4rem; color: #e8d48a; }}
    p, .note {{ color: #a89f8c; font-size: 0.95rem; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }}
    .summary div {{ border: 1px solid #4a4030; padding: 0.75rem 1rem; min-width: 7rem; }}
    .summary strong {{ display: block; font-size: 1.4rem; color: #e8d48a; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; font-size: 0.9rem; }}
    th, td {{ border: 1px solid #4a4030; padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
    th {{ background: rgba(0,0,0,0.45); color: #e8d48a; }}
    code {{ font-size: 0.8rem; color: #d4b86a; }}
  </style>
</head>
<body>
  <h1>Operator analytics</h1>
  <p>Hashed IP only (no raw addresses). One visit per IP per UTC day; every Ask is logged.</p>
  <div class="summary">
    <div><strong>{summary["unique_visitors"]}</strong>Unique visitors</div>
    <div><strong>{summary["total_visits"]}</strong>Visits</div>
    <div><strong>{summary["total_asks"]}</strong>Asks</div>
    <div><strong>{summary["asks_last_24h"]}</strong>Asks (24h)</div>
  </div>
  <p class="note">Country shows when a proxy sends it (e.g. Cloudflare). Local runs usually show —.
  This database is only for <em>this</em> server — open the matching URL (local vs production). Persist Railway data with a volume on <code>/app/data</code>.</p>
  <table>
    <thead>
      <tr><th>UTC time</th><th>Action</th><th>Country</th><th>IP hash</th></tr>
    </thead>
    <tbody>
      {body_rows}
    </tbody>
  </table>
</body>
</html>
"""
