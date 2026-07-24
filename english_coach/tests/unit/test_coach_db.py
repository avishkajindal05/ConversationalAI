# ─── tests/unit/test_coach_db.py ───
"""SQLite persistence: save, latest open issues, cross-session history."""

from __future__ import annotations

import pytest

from english_coach.v2.coach.schema import Analysis


@pytest.fixture()
def coach_db(tmp_path, monkeypatch):
    """Point coach.db at a temp file and return the module."""
    import english_coach.v2.coach.db as db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "coach.db")
    db.init_db()
    return db


def _analysis(**scores) -> Analysis:
    return Analysis.model_validate(
        {
            "scores": scores or {"fluency": 60, "clarity": 60, "vocabulary": 60, "grammar": 60, "confidence": 60},
            "summary": "s",
            "new_issues": [{"description": "filler words", "category": "fluency", "severity": "low"}],
        }
    )


def test_save_and_latest_open_issues(coach_db):
    a = _analysis()
    open_issues = a.open_issues([])
    sid = coach_db.save_session("cand1", "live", "User: hi", a, open_issues)
    assert sid > 0

    latest = coach_db.latest_open_issues("cand1")
    assert [i["description"] for i in latest] == ["filler words"]


def test_all_sessions_oldest_first(coach_db):
    coach_db.save_session("c", "live", "t1", _analysis(fluency=50, clarity=50, vocabulary=50, grammar=50, confidence=50), [])
    coach_db.save_session("c", "live", "t2", _analysis(fluency=80, clarity=80, vocabulary=80, grammar=80, confidence=80), [])
    sessions = coach_db.all_sessions("c")
    assert len(sessions) == 2
    assert sessions[0]["overall_score"] == 50.0
    assert sessions[1]["overall_score"] == 80.0


def test_unknown_candidate_is_empty(coach_db):
    assert coach_db.all_sessions("nobody") == []
    assert coach_db.latest_open_issues("nobody") == []
