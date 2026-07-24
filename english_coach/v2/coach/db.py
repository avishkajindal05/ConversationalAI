# ─── coach/db.py ───
"""Tiny SQLite persistence: one table, JSON columns for nested data.

Enough to prove "iterative feedback across sessions" without a multi-table
relational model. Uses the stdlib sqlite3 (no ORM) to stay lean.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("data/coach.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id   TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    source         TEXT NOT NULL,
    transcript     TEXT,
    overall_score  REAL,
    scores_json    TEXT,
    summary        TEXT,
    strengths_json TEXT,
    verdicts_json  TEXT,
    new_issues_json TEXT,
    open_issues_json TEXT
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_SCHEMA)


def save_session(
    candidate_id: str,
    source: str,
    transcript: str,
    analysis: Any,
    open_issues: list[dict],
) -> int:
    """Persist one analysed session; returns its row id."""
    init_db()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO sessions (
                candidate_id, created_at, source, transcript, overall_score,
                scores_json, summary, strengths_json, verdicts_json,
                new_issues_json, open_issues_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_id,
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                source,
                transcript,
                analysis.overall_score,
                json.dumps(analysis.scores.model_dump()),
                analysis.summary,
                json.dumps(analysis.strengths),
                json.dumps([v.model_dump() for v in analysis.prior_issue_verdicts]),
                json.dumps([i.model_dump() for i in analysis.new_issues]),
                json.dumps(open_issues),
            ),
        )
        return int(cur.lastrowid)


def latest_open_issues(candidate_id: str) -> list[dict]:
    """Open issues carried out of this candidate's most recent session."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT open_issues_json FROM sessions WHERE candidate_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (candidate_id,),
        ).fetchone()
    if not row or not row["open_issues_json"]:
        return []
    return json.loads(row["open_issues_json"])


def all_sessions(candidate_id: str) -> list[dict]:
    """Every session for a candidate, oldest first, with JSON columns parsed."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE candidate_id = ? ORDER BY id ASC",
            (candidate_id,),
        ).fetchall()
    sessions: list[dict] = []
    for row in rows:
        sessions.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "source": row["source"],
                "overall_score": row["overall_score"],
                "scores": json.loads(row["scores_json"] or "{}"),
                "summary": row["summary"] or "",
                "strengths": json.loads(row["strengths_json"] or "[]"),
                "verdicts": json.loads(row["verdicts_json"] or "[]"),
                "new_issues": json.loads(row["new_issues_json"] or "[]"),
                "open_issues": json.loads(row["open_issues_json"] or "[]"),
            }
        )
    return sessions
