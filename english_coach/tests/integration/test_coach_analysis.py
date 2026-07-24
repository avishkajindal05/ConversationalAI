# ─── tests/integration/test_coach_analysis.py ───
"""analyze() parses/validates model output and retries on bad JSON (mock LLM)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from english_coach.v2.coach.analysis import NOT_ENOUGH_SUMMARY, analyze

_GOOD = {
    "scores": {"fluency": 70, "clarity": 65, "vocabulary": 60, "grammar": 80, "confidence": 55},
    "summary": "Solid, clear answers.",
    "strengths": ["clear structure"],
    "prior_issue_verdicts": [
        {"description": "filler words", "status": "improved", "evidence": "fewer 'um's"}
    ],
    "new_issues": [{"description": "long pauses", "category": "fluency", "severity": "low"}],
}


# A transcript with enough user speech to clear the min-content guard, so these
# tests exercise the LLM/validation path rather than the too-short shortcut.
_TRANSCRIPT = (
    "Coach: What have you been up to?\n"
    "User: I have been practising presentations at work and trying to slow down "
    "when I speak so my points land more clearly with the team."
)


class _Resp:
    def __init__(self, content):
        self.content = content


def test_analyze_parses_valid_json():
    llm = MagicMock()
    llm.invoke.return_value = _Resp(json.dumps(_GOOD))
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze(_TRANSCRIPT, prior_issues=[{"description": "filler words"}])

    assert result.scores.grammar == 80
    assert result.overall_score == 66.0
    assert result.prior_issue_verdicts[0].status == "improved"
    assert result.new_issues[0].description == "long pauses"


def test_analyze_retries_then_succeeds():
    llm = MagicMock()
    llm.invoke.side_effect = [_Resp("not json"), _Resp(json.dumps(_GOOD))]
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze(_TRANSCRIPT, prior_issues=[{"description": "filler words"}])
    assert result.summary == "Solid, clear answers."
    assert llm.invoke.call_count == 2


def test_analyze_accepts_partial_prior_coverage_without_retry():
    # A response that omits a prior-issue verdict is accepted (no retry); the
    # unjudged issue is carried forward as still-open rather than failing.
    incomplete = {**_GOOD, "prior_issue_verdicts": []}
    llm = MagicMock()
    llm.invoke.return_value = _Resp(json.dumps(incomplete))
    prior = [{"description": "filler words", "category": "fluency", "severity": "low"}]
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze(_TRANSCRIPT, prior_issues=prior)

    assert llm.invoke.call_count == 1
    assert any(i["description"] == "filler words" for i in result.open_issues(prior))


def test_analyze_refuses_near_empty_transcript_without_calling_model():
    # Guard: too little user speech must NOT be scored — a small model otherwise
    # fabricates a glowing 80-95 report from nothing. The LLM is never called.
    llm = MagicMock()
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze("Coach: Hi there!\nUser: hi", prior_issues=[])
    assert llm.invoke.call_count == 0
    assert result.summary == NOT_ENOUGH_SUMMARY


def test_analyze_guard_keeps_prior_issues_open():
    # A too-short transcript must not silently resolve issues from last session.
    prior = [{"description": "filler words", "category": "fluency", "severity": "medium"}]
    llm = MagicMock()
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze("User: yes", prior_issues=prior)
    assert any(i["description"] == "filler words" for i in result.open_issues(prior))


def test_analyze_evaluates_a_real_short_answer():
    # A genuine short answer (>= the word threshold) is still evaluated normally.
    llm = MagicMock()
    llm.invoke.return_value = _Resp(json.dumps(_GOOD))
    transcript = (
        "Coach: What have you been up to?\n"
        "User: I spent the weekend hiking with friends and cooking a big dinner, "
        "it was relaxing and I felt recharged."
    )
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze(transcript, prior_issues=[])
    assert llm.invoke.call_count == 1
    assert result.summary == "Solid, clear answers."


def test_analyze_returns_safe_default_when_all_attempts_fail():
    llm = MagicMock()
    llm.invoke.return_value = _Resp("still not json")
    with patch("english_coach.v2.coach.analysis.ChatOllama", return_value=llm):
        result = analyze(_TRANSCRIPT, prior_issues=[])
    # Never raises; returns a valid Analysis with default scores.
    assert result.overall_score == 50.0
    assert "could not be completed" in result.summary.lower()
