# ─── reports/pdf_report.py ───
"""Render an evaluation report dict to PDF bytes (fpdf2)."""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

_SKILL_ORDER = ["grammar", "vocabulary", "fluency", "engagement", "confidence"]


def _clean(text: str) -> str:
    """fpdf2's core fonts are latin-1 only; drop anything outside it."""
    return str(text).encode("latin-1", "replace").decode("latin-1")


def build_report_pdf(report: dict[str, Any]) -> bytes:
    """Build a one-page PDF summary from a report dict."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, _clean("English Coach - Session Report"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, _clean(f"Overall score: {report.get('overall_score', 0):.0f} / 100"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    summary = report.get("summary")
    if summary:
        pdf.set_font("Helvetica", "", 11)
        _para(pdf, _clean(summary))
        pdf.ln(2)

    # Per-skill scores
    scores = report.get("scores", {})
    if scores:
        _heading(pdf, "Scores")
        pdf.set_font("Helvetica", "", 11)
        for skill in _SKILL_ORDER:
            value = scores.get(skill, {})
            score = value.get("score") if isinstance(value, dict) else None
            if score is not None:
                pdf.cell(0, 6, _clean(f"  {skill.capitalize()}: {score}"),
                         new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    _bullet_section(pdf, "Strengths", report.get("strengths", []))
    _bullet_section(pdf, "Weaknesses", report.get("weaknesses", []))

    recommendation = report.get("recommendation", {})
    if recommendation:
        _heading(pdf, "Next steps")
        pdf.set_font("Helvetica", "", 11)
        _para(pdf, _clean(f"Goal: {recommendation.get('next_session_goal', '')}"))
        _para(pdf, _clean(f"Homework: {recommendation.get('homework', '')}"))
        for exercise in recommendation.get("exercises", []):
            _para(pdf, _clean(f"  - {exercise}"))

    # fpdf2 returns a bytearray; normalise to bytes.
    return bytes(pdf.output())


def _para(pdf: FPDF, text: str) -> None:
    """multi_cell that returns the cursor to the left margin on the next line.

    (fpdf2's multi_cell defaults to leaving x at the right margin, which
    starves any following multi_cell of horizontal space.)"""
    pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")


def _heading(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _clean(text), new_x="LMARGIN", new_y="NEXT")


def _bullet_section(pdf: FPDF, title: str, items: list) -> None:
    if not items:
        return
    _heading(pdf, title)
    pdf.set_font("Helvetica", "", 11)
    for item in items:
        _para(pdf, _clean(f"  - {item}"))
    pdf.ln(1)
