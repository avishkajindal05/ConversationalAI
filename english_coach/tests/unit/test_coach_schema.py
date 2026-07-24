# ─── tests/unit/test_coach_schema.py ───
"""Schema validation + open-issue carry-forward logic."""

from __future__ import annotations

import pytest

from english_coach.v2.coach.schema import Analysis, Scores, validate_llm_payload


def test_scores_clamp_and_coerce():
    s = Scores(fluency=120, clarity=-5, vocabulary="80", grammar=50.6, confidence="oops")
    assert s.fluency == 100
    assert s.clarity == 0
    assert s.vocabulary == 80
    assert s.grammar == 51
    assert s.confidence == 50  # unparseable -> default


def test_overall_score_is_mean():
    a = Analysis(scores=Scores(fluency=80, clarity=60, vocabulary=70, grammar=50, confidence=90))
    assert a.overall_score == 70.0


def test_open_issues_carries_unchanged_and_worse_plus_new():
    prior = [
        {"description": "hedging language", "category": "confidence", "severity": "high"},
        {"description": "run-on sentences", "category": "grammar", "severity": "medium"},
        {"description": "filler words", "category": "fluency", "severity": "low"},
    ]
    a = Analysis.model_validate(
        {
            "scores": {"fluency": 70, "clarity": 70, "vocabulary": 70, "grammar": 70, "confidence": 70},
            "summary": "ok",
            "prior_issue_verdicts": [
                {"description": "hedging language", "status": "worse", "evidence": "more 'maybe'"},
                {"description": "run-on sentences", "status": "improved", "evidence": "shorter"},
                {"description": "filler words", "status": "unchanged", "evidence": "still 'um'"},
            ],
            "new_issues": [
                {"description": "monotone delivery", "category": "confidence", "severity": "medium"}
            ],
        }
    )
    open_issues = a.open_issues(prior)
    descs = {i["description"] for i in open_issues}
    # improved -> dropped; unchanged/worse -> kept; new -> added
    assert "run-on sentences" not in descs
    assert "hedging language" in descs
    assert "filler words" in descs
    assert "monotone delivery" in descs
    # carried-forward issue keeps its original category/severity
    hedging = next(i for i in open_issues if i["description"] == "hedging language")
    assert hedging["severity"] == "high"


def test_analysis_defaults_are_safe():
    a = Analysis()
    assert a.overall_score == 50.0
    assert a.open_issues([]) == []


def test_open_issues_keeps_prior_issue_when_verdict_is_omitted():
    prior = [{"description": "filler words", "category": "fluency", "severity": "low"}]
    analysis = Analysis()
    assert analysis.open_issues(prior) == prior


def test_llm_payload_requires_complete_scores_and_prior_verdict_coverage():
    payload = {
        "scores": {"fluency": 60, "clarity": 60, "vocabulary": 60, "grammar": 60},
        "summary": "s",
        "strengths": [],
        "prior_issue_verdicts": [],
        "new_issues": [],
    }
    with pytest.raises(ValueError, match="all five score metrics"):
        validate_llm_payload(payload, [])

    payload["scores"]["confidence"] = 60
    with pytest.raises(ValueError, match="one verdict for every prior issue"):
        validate_llm_payload(payload, [{"description": "filler words"}])
