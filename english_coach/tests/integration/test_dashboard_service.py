# ─── tests/integration/test_dashboard_service.py ───
"""get_user_history assembles session + report rows for the dashboard."""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import english_coach.services.dashboard_service as dashboard_service
from english_coach.database.connection import Base
from english_coach.database.dao.learner_dao import LearnerDAO
from english_coach.database.dao.report_dao import ReportDAO
from english_coach.database.dao.session_dao import SessionDAO


def test_get_user_history_oldest_first(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dash.db'}", future=True)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Seed two evaluated sessions for one user.
    db = TestSession()
    LearnerDAO(db).get_or_create_user("u1")
    for i, score in enumerate([60.0, 72.0], start=1):
        sid = f"s{i}"
        SessionDAO(db).create({"session_id": sid, "user_id": "u1"})
        SessionDAO(db).end_session(sid, overall_score=score)
        ReportDAO(db).create(
            {
                "report_id": f"r{i}",
                "session_id": sid,
                "overall_score": score,
                "report": {"overall_score": score, "scores": {"grammar": {"score": score}}},
            }
        )
    db.close()

    with patch.object(dashboard_service, "SessionLocal", TestSession):
        history = dashboard_service.get_user_history("u1")

    assert [row["overall_score"] for row in history] == [60.0, 72.0]  # oldest first
    assert history[0]["grammar"] == 60.0
    assert history[1]["session_id"] == "s2"


def test_get_user_history_empty_for_unknown_user(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dash2.db'}", future=True)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with patch.object(dashboard_service, "SessionLocal", TestSession):
        assert dashboard_service.get_user_history("ghost") == []
