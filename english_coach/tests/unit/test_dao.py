# ─── tests/unit/test_dao.py ───
"""DAO round-trip tests against an isolated temp SQLite database."""

from __future__ import annotations

from english_coach.database.dao.learner_dao import LearnerDAO
from english_coach.database.dao.report_dao import ReportDAO
from english_coach.database.dao.session_dao import SessionDAO


def test_learner_profile_round_trip(db_session):
    dao = LearnerDAO(db_session)
    dao.create(
        {
            "user_id": "u1",
            "estimated_level": "B1",
            "overall_score": 70.0,
            "grammar": {"score": 75, "common_errors": ["articles"]},
        }
    )
    record = dao.get_by_id("u1")
    assert record.estimated_level == "B1"
    assert record.grammar_json["common_errors"] == ["articles"]

    dao.update("u1", {"overall_score": 82.5, "estimated_level": "B2"})
    record = dao.get_by_id("u1")
    assert record.overall_score == 82.5
    assert record.estimated_level == "B2"


def test_update_creates_when_missing(db_session):
    dao = LearnerDAO(db_session)
    record = dao.update("ghost", {"overall_score": 55.0})
    assert record is not None
    assert dao.get_by_id("ghost").overall_score == 55.0


def test_session_and_messages_round_trip(db_session):
    dao = SessionDAO(db_session)
    LearnerDAO(db_session).get_or_create_user("u2")
    dao.create({"session_id": "s1", "user_id": "u2"})

    dao.add_message("s1", "user", "hello")
    dao.add_message("s1", "assistant", "hi there")
    messages = dao.get_messages("s1")
    assert [(m.speaker, m.text) for m in messages] == [
        ("user", "hello"),
        ("assistant", "hi there"),
    ]

    ended = dao.end_session("s1", overall_score=88.0)
    assert ended.status == "completed"
    assert ended.overall_score == 88.0
    assert ended.ended_at is not None


def test_report_round_trip(db_session):
    LearnerDAO(db_session).get_or_create_user("u3")
    SessionDAO(db_session).create({"session_id": "s2", "user_id": "u3"})
    rdao = ReportDAO(db_session)
    rdao.create(
        {
            "report_id": "r1",
            "session_id": "s2",
            "overall_score": 61.2,
            "report": {"summary": "good work"},
        }
    )
    assert rdao.get_by_id("r1").report_json["summary"] == "good work"
    assert len(rdao.list_by_session("s2")) == 1
