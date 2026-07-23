# ─── tests/unit/test_pdf_report.py ───
"""The PDF builder produces a valid, non-empty PDF."""

from __future__ import annotations

from english_coach.reports.pdf_report import build_report_pdf

_REPORT = {
    "session_id": "abc",
    "overall_score": 68.1,
    "summary": "Good progress this session. Keep practicing past tense.",
    "strengths": ["Fluency", "Vocabulary"],
    "weaknesses": ["Grammar accuracy"],
    "progress": "Up 6 points from last time.",
    "scores": {
        "grammar": {"score": 60},
        "vocabulary": {"score": 82},
        "fluency": {"score": 80},
        "engagement": {"score": 62},
        "confidence": {"score": 68},
    },
    "recommendation": {
        "next_session_goal": "Practice past tense",
        "homework": "Describe yesterday for five minutes.",
        "exercises": ["Verb drill", "Story retelling"],
    },
}


def test_build_report_pdf_returns_pdf_bytes():
    data = build_report_pdf(_REPORT)
    assert isinstance(data, (bytes, bytearray))
    assert bytes(data[:4]) == b"%PDF"
    assert len(data) > 500


def test_build_report_pdf_handles_minimal_report():
    data = build_report_pdf({"overall_score": 0})
    assert bytes(data[:4]) == b"%PDF"


def test_build_report_pdf_handles_non_latin1_text():
    # Curly quotes / emoji must not crash the latin-1 core font.
    data = build_report_pdf({"overall_score": 50, "summary": "Great job — keep going! \U0001f389"})
    assert bytes(data[:4]) == b"%PDF"
