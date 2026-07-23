# ─── tests/integration/test_profile_update.py ───
"""SessionService._update_profile maps evaluation output onto the profile."""

from __future__ import annotations

from unittest.mock import patch

from english_coach.memory.learner_profile import LearnerProfile
from english_coach.memory.session_state import SessionState
from english_coach.services.session_service import session_service


def _result_state() -> SessionState:
    state = SessionState()
    state.user.user_id = "u42"
    state.scores = {
        "grammar": {"score": 82, "common_errors": ["articles", "tense"]},
        "vocabulary": {"score": 66, "lexical_diversity": 0.5, "weaknesses": ["idioms"]},
        "engagement": {"score": 70, "average_words": 30, "follow_up_questions": 2},
        "confidence": {"score": 60, "hedging_frequency": 0.2, "notes": "some hedging"},
    }
    state.evaluation.recommendation = {
        "next_session_goal": "Practice idioms",
        "homework": "Use five idioms in sentences.",
        "exercises": ["idiom drill"],
        "conversation_topics": ["Culture"],
    }
    state.report.data = {"overall_score": 74.0}
    return state


def test_update_profile_writes_scores_and_recommendation():
    saved = {}

    def fake_load(user_id):
        return LearnerProfile(user_id=user_id, estimated_level="B1")

    def fake_save(profile):
        saved["profile"] = profile

    with patch("english_coach.services.session_service.profile_service") as ps:
        ps.load.side_effect = fake_load
        ps.save.side_effect = fake_save
        session_service._update_profile("u42", "sess-42", _result_state())

    profile = saved["profile"]
    assert profile.overall_score == 74.0
    assert profile.grammar.score == 82
    assert profile.grammar.common_errors == ["articles", "tense"]
    assert profile.vocabulary.weaknesses == ["idioms"]
    assert profile.recommendation.next_session_goal == "Practice idioms"
    assert profile.recommended_topics == ["Culture"]
    assert "sess-42" in profile.session_history
