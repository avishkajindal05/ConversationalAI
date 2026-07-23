# ─── tests/unit/test_pure_functions.py ───
"""Unit tests for the deterministic helpers (no LLM, no DB)."""

from __future__ import annotations

from english_coach.agents.evaluation.recommendation import derive_goal
from english_coach.agents.evaluation.report import ReportAgent
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import merge_scores
from english_coach.services.session_service import _advance_level


def test_merge_scores_combines_disjoint_keys():
    assert merge_scores({"grammar": 1}, {"vocabulary": 2}) == {
        "grammar": 1,
        "vocabulary": 2,
    }


def test_merge_scores_handles_none():
    assert merge_scores(None, {"a": 1}) == {"a": 1}
    assert merge_scores({"a": 1}, None) == {"a": 1}


def test_derive_goal_picks_first_weak_dimension():
    scores = {"grammar": {"score": 40}, "vocabulary": {"score": 90}}
    assert "past tense" in derive_goal(scores).lower()


def test_derive_goal_defaults_when_all_strong():
    scores = {"grammar": {"score": 90}, "vocabulary": {"score": 88}}
    assert derive_goal(scores) == "Keep building overall conversational fluency"


def test_weighted_overall_is_weighted_mean():
    scores = {
        "grammar": {"score": 80},
        "vocabulary": {"score": 60},
        "fluency": {"score": 70},
        "engagement": {"score": 50},
        "confidence": {"score": 90},
    }
    result = ReportAgent._weighted_overall(scores)
    expected = 80 * 0.3 + 60 * 0.25 + 70 * 0.2 + 50 * 0.15 + 90 * 0.1
    assert result == round(expected, 1)


def test_weighted_overall_ignores_missing_scores():
    assert ReportAgent._weighted_overall({}) == 0.0


def test_advance_level_only_on_high_score():
    assert _advance_level("A2", 90) == "B1"
    assert _advance_level("A2", 70) == "A2"
    assert _advance_level("C2", 99) == "C2"  # already at top


def test_parse_json_recovers_embedded_object():
    raw = "Sure! Here is the result:\n{\"score\": 72}\nHope that helps."
    assert EvaluationModel._parse_json(raw, {"score": 0}) == {"score": 72}


def test_parse_json_falls_back_on_garbage():
    assert EvaluationModel._parse_json("not json at all", {"score": -1}) == {"score": -1}
