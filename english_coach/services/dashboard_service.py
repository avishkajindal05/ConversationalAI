# ─── services/dashboard_service.py ───
"""Assembles a learner's session history for the progress dashboard."""

from __future__ import annotations

from typing import Any

from english_coach.database.connection import SessionLocal
from english_coach.database.dao.report_dao import ReportDAO
from english_coach.database.dao.session_dao import SessionDAO

_SKILLS = ["grammar", "vocabulary", "fluency", "engagement", "confidence"]


def get_user_history(user_id: str) -> list[dict[str, Any]]:
    """Return one row per evaluated session, oldest first.

    Each row: {session_id, date, overall_score, grammar, vocabulary, ...}
    so the frontend can chart score trends over time.
    """
    db = SessionLocal()
    try:
        session_dao = SessionDAO(db)
        report_dao = ReportDAO(db)
        rows: list[dict[str, Any]] = []
        for session in session_dao.list_by_user(user_id):
            reports = report_dao.list_by_session(session.session_id)
            if not reports:
                continue
            report = reports[-1].report_json or {}
            scores = report.get("scores", {})
            row = {
                "session_id": session.session_id,
                "date": (session.started_at.isoformat() if session.started_at else ""),
                "overall_score": report.get("overall_score", session.overall_score),
            }
            for skill in _SKILLS:
                value = scores.get(skill, {})
                row[skill] = value.get("score") if isinstance(value, dict) else None
            rows.append(row)
        # list_by_user is newest-first; charts read better oldest-first.
        rows.reverse()
        return rows
    finally:
        db.close()
