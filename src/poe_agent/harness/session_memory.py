# ROLE: harness — session conversation memory (SQLite + optional rolling summary).

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from poe_agent.harness.config import Settings, get_settings

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_SUMMARY_SYSTEM = """You maintain a compact running summary of a Path of Exile 1 Q&A chat.
Update the summary with new turns. Keep topics, mechanic names, and unresolved references.
Max ~120 words. No wiki dump. Plain prose or short bullets."""


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_utc TEXT NOT NULL,
            updated_utc TEXT NOT NULL,
            summary TEXT NOT NULL DEFAULT '',
            summary_through_id INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Migrate older DBs missing summary columns
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()}
    if "summary" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT NOT NULL DEFAULT ''")
    if "summary_through_id" not in cols:
        conn.execute(
            "ALTER TABLE sessions ADD COLUMN summary_through_id INTEGER NOT NULL DEFAULT 0"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            ts_utc TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            citations_json TEXT NOT NULL DEFAULT '[]',
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
        """
    )
    turn_cols = {r[1] for r in conn.execute("PRAGMA table_info(turns)").fetchall()}
    if "citations_json" not in turn_cols:
        conn.execute(
            "ALTER TABLE turns ADD COLUMN citations_json TEXT NOT NULL DEFAULT '[]'"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, id)"
    )
    conn.commit()
    return conn


def normalize_session_id(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    sid = str(raw).strip()
    if not _UUID_RE.match(sid):
        return None
    return sid.lower()


def ensure_session(
    session_id: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Return a valid session id, creating a new session row when needed."""
    s = settings or get_settings()
    sid = normalize_session_id(session_id) or str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect(s.session_memory_db_path) as conn:
        row = conn.execute("SELECT id FROM sessions WHERE id = ?", (sid,)).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO sessions (id, created_utc, updated_utc, summary, summary_through_id)
                VALUES (?, ?, ?, '', 0)
                """,
                (sid, now, now),
            )
            conn.commit()
    return sid


def load_all_turns(
    session_id: str,
    settings: Settings | None = None,
) -> list[dict[str, str]]:
    """Oldest-first list of all turns for a session (no turn-count cap)."""
    s = settings or get_settings()
    if not s.session_memory_enabled:
        return []
    sid = normalize_session_id(session_id)
    if not sid:
        return []
    with _connect(s.session_memory_db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, question, answer FROM turns
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (sid,),
        ).fetchall()
    return [
        {"id": str(r[0]), "question": str(r[1]), "answer": str(r[2])}
        for r in rows
    ]


def load_recent_turns(
    session_id: str,
    *,
    limit: int | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """Oldest-first recent verbatim turns (window for prompts), including citations."""
    s = settings or get_settings()
    if not s.session_memory_enabled:
        return []
    sid = normalize_session_id(session_id)
    if not sid:
        return []
    lim = limit if limit is not None else max(1, int(s.session_memory_recent_turns))
    lim = max(1, min(int(lim), 100))
    with _connect(s.session_memory_db_path) as conn:
        rows = conn.execute(
            """
            SELECT question, answer, citations_json FROM turns
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (sid, lim),
        ).fetchall()
    rows.reverse()
    out: list[dict] = []
    for r in rows:
        citations: list[dict] = []
        try:
            raw = json.loads(r[2] or "[]")
            if isinstance(raw, list):
                citations = [
                    {"title": str(c.get("title", "")), "url": str(c.get("url", ""))}
                    for c in raw
                    if isinstance(c, dict)
                ]
        except json.JSONDecodeError:
            citations = []
        out.append(
            {
                "question": str(r[0]),
                "answer": str(r[1]),
                "citations": citations,
            }
        )
    return out


def get_session_summary(
    session_id: str,
    settings: Settings | None = None,
) -> str:
    s = settings or get_settings()
    sid = normalize_session_id(session_id)
    if not sid:
        return ""
    with _connect(s.session_memory_db_path) as conn:
        row = conn.execute(
            "SELECT summary FROM sessions WHERE id = ?", (sid,)
        ).fetchone()
    return str(row[0]) if row and row[0] else ""


def load_prompt_history(
    session_id: str,
    settings: Settings | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Return (summary, recent_verbatim_turns) for generation/planner context."""
    s = settings or get_settings()
    if not s.session_memory_enabled:
        return "", []
    sid = normalize_session_id(session_id)
    if not sid:
        return "", []
    recent = load_recent_turns(sid, settings=s)
    summary = get_session_summary(sid, settings=s) if s.session_memory_summary_enabled else ""
    return summary, recent


def history_search_hints(
    history: list[dict],
    *,
    max_hints: int = 8,
) -> list[str]:
    """Topic/entity strings and prior citation page titles for wiki search extras."""
    from poe_agent.retriever.query_fusion import (
        extract_mechanic_entities,
        extract_topic_terms,
    )

    hints: list[str] = []
    seen: set[str] = set()

    def _add(term: str) -> bool:
        key = term.casefold().strip()
        if not key or len(key) < 2 or key in seen:
            return False
        seen.add(key)
        hints.append(term.strip())
        return len(hints) >= max_hints

    # Prefer prior wiki page titles first (continuity of Sources)
    for turn in history[-8:]:
        for cite in turn.get("citations") or []:
            title = str(cite.get("title") or "").strip()
            if title and _add(title):
                return hints

    for turn in history[-8:]:
        q = turn.get("question") or ""
        for term in extract_mechanic_entities(q) + extract_topic_terms(q):
            if _add(term):
                return hints
    return hints


def history_page_titles(history: list[dict], *, max_titles: int = 6) -> list[str]:
    """Prior citation page titles for live title probes."""
    titles: list[str] = []
    seen: set[str] = set()
    for turn in history[-8:]:
        for cite in turn.get("citations") or []:
            title = str(cite.get("title") or "").strip()
            key = title.casefold()
            if not title or key in seen:
                continue
            seen.add(key)
            titles.append(title)
            if len(titles) >= max_titles:
                return titles
    return titles


def append_turn(
    session_id: str,
    question: str,
    answer: str,
    settings: Settings | None = None,
    citations: list[dict] | None = None,
) -> None:
    s = settings or get_settings()
    if not s.session_memory_enabled:
        return
    sid = ensure_session(session_id, settings=s)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cite_payload = []
    for c in citations or []:
        title = str(c.get("title") or "").strip()
        url = str(c.get("url") or "").strip()
        if title or url:
            cite_payload.append({"title": title[:300], "url": url[:500]})
    cite_json = json.dumps(cite_payload[:20])
    with _connect(s.session_memory_db_path) as conn:
        conn.execute(
            """
            INSERT INTO turns (session_id, ts_utc, question, answer, citations_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sid, now, (question or "")[:8000], (answer or "")[:32000], cite_json),
        )
        conn.execute(
            "UPDATE sessions SET updated_utc = ? WHERE id = ?",
            (now, sid),
        )
        conn.commit()
    maybe_refresh_summary(sid, settings=s)


def maybe_refresh_summary(
    session_id: str,
    settings: Settings | None = None,
) -> None:
    """Roll older turns into sessions.summary when beyond the recent window."""
    s = settings or get_settings()
    if not s.session_memory_enabled or not s.session_memory_summary_enabled:
        return
    sid = normalize_session_id(session_id)
    if not sid:
        return
    recent_n = max(1, int(s.session_memory_recent_turns))
    with _connect(s.session_memory_db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, question, answer FROM turns
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (sid,),
        ).fetchall()
        meta = conn.execute(
            "SELECT summary, summary_through_id FROM sessions WHERE id = ?",
            (sid,),
        ).fetchone()
    if len(rows) <= recent_n:
        return
    older = rows[:-recent_n]
    prev_summary = str(meta[0]) if meta and meta[0] else ""
    through_id = int(meta[1]) if meta else 0
    new_older = [r for r in older if int(r[0]) > through_id]
    if not new_older:
        return
    block_lines = []
    if prev_summary.strip():
        block_lines.append(f"Existing summary:\n{prev_summary.strip()}")
    block_lines.append("New turns to fold in:")
    for r in new_older:
        block_lines.append(f"User: {r[1]}\nAssistant: {r[2]}")
    user_prompt = "\n\n".join(block_lines) + "\n\nReturn the updated summary only."
    try:
        from poe_agent.harness.providers import get_llm_provider

        llm = get_llm_provider()
        text, _ = llm.generate(_SUMMARY_SYSTEM, user_prompt)
        summary = (text or "").strip()[:4000]
    except Exception:
        # Fallback: concatenate truncated older Qs if LLM unavailable
        bits = [f"- {r[1][:120]}" for r in older[-12:]]
        summary = (prev_summary + "\n" if prev_summary else "") + "\n".join(bits)
        summary = summary.strip()[:4000]
    max_id = int(older[-1][0])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _connect(s.session_memory_db_path) as conn:
        conn.execute(
            """
            UPDATE sessions
            SET summary = ?, summary_through_id = ?, updated_utc = ?
            WHERE id = ?
            """,
            (summary, max_id, now, sid),
        )
        conn.commit()


def format_history_block(turns: list[dict[str, str]]) -> str:
    if not turns:
        return ""
    parts: list[str] = []
    for i, turn in enumerate(turns, start=1):
        parts.append(
            f"Turn {i}\nUser: {turn['question']}\nAssistant: {turn['answer']}"
        )
    return "\n\n".join(parts)


def format_generation_context(
    summary: str,
    recent_turns: list[dict[str, str]],
) -> str:
    parts: list[str] = []
    if summary.strip():
        parts.append(f"Summary of earlier conversation:\n{summary.strip()}")
    block = format_history_block(recent_turns)
    if block:
        parts.append(f"Recent turns:\n{block}")
    return "\n\n".join(parts)
