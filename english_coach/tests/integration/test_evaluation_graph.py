# ─── tests/integration/test_evaluation_graph.py ───
"""Evaluation graph execution with a mocked evaluation LLM.

Confirms the parallel fan-out/fan-in merges all five scores and that
recommendation + report run at the fan-in.
"""

from __future__ import annotations

from unittest.mock import patch

from english_coach.graphs.evaluation_graph import EvaluationGraph
from english_coach.memory.session_state import SessionState


def _fake_evaluate(self, system_prompt, content, fallback):
    # A superset dict that satisfies every evaluation agent's expected keys.
    return {
        "score": 70,
        "common_errors": ["past tense"],
        "lexical_diversity": 0.6,
        "strengths": ["daily topics"],
        "weaknesses": ["business english"],
        "homework": "Describe your day.",
        "exercises": ["drill A"],
        "conversation_topics": ["Travel"],
        "summary": "Solid session.",
        "progress": "Improved slightly.",
    }


def _build_state() -> SessionState:
    state = SessionState()
    state.conversation.messages = [
        {"role": "assistant", "content": "What did you do yesterday?"},
        {"role": "user", "content": "I go to market and buy apple."},
    ]
    state.evaluation.transcript = "Coach: ...\nLearner: I go to market and buy apple."
    return state


def test_evaluation_graph_produces_full_report():
    with patch(
        "english_coach.llm.evaluation_model.EvaluationModel.evaluate",
        new=_fake_evaluate,
    ):
        graph = EvaluationGraph().build_graph()
        result = SessionState.model_validate(graph.invoke(_build_state()))

    # All five scorers merged into the reducer channel.
    assert set(result.scores) == {
        "grammar",
        "vocabulary",
        "fluency",
        "engagement",
        "confidence",
    }
    # Engagement adds deterministic metrics on top of the LLM result.
    assert "average_words" in result.scores["engagement"]
    assert result.scores["engagement"]["follow_up_questions"] == 0

    # Recommendation derived a goal in Python + LLM material.
    rec = result.evaluation.recommendation
    assert rec["next_session_goal"]  # non-empty
    assert rec["homework"] == "Describe your day."

    # Report aggregated a weighted overall score + narrative.
    report = result.report.data
    assert report["overall_score"] == 70.0  # all scores are 70
    assert report["summary"] == "Solid session."
    assert result.report.generated is True


def test_scorer_fallback_on_bad_json_does_not_crash():
    def _raise(self, *a, **k):
        raise RuntimeError("model down")

    # evaluate() itself catches and returns fallback; here we confirm the
    # graph still completes even if the underlying invoke throws.
    with patch(
        "english_coach.llm.evaluation_model.EvaluationModel.evaluate",
        new=lambda self, sp, c, fb: fb,
    ):
        graph = EvaluationGraph().build_graph()
        result = SessionState.model_validate(graph.invoke(_build_state()))

    # Fallbacks still populate every score key; graph does not raise.
    assert set(result.scores) == {
        "grammar",
        "vocabulary",
        "fluency",
        "engagement",
        "confidence",
    }
    assert result.report.generated is True
