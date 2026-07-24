# ─── coach/schema.py ───
"""Pydantic models for the structured communication analysis.

The app branches on these values (issue verdicts, severities), so the LLM's
output is validated against this schema rather than trusted as free text.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

METRICS = ["fluency", "clarity", "vocabulary", "grammar", "confidence"]

Status = Literal["improved", "unchanged", "worse"]
Severity = Literal["low", "medium", "high"]
Category = Literal["fluency", "clarity", "vocabulary", "grammar", "confidence", "general"]


class Scores(BaseModel):
    """0-100 communication scores across the five tracked metrics."""

    fluency: int = 50
    clarity: int = 50
    vocabulary: int = 50
    grammar: int = 50
    confidence: int = 50

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_and_clamp(cls, v: object) -> int:
        try:
            n = int(round(float(v)))
        except (TypeError, ValueError):
            return 50
        return max(0, min(100, n))

    def mean(self) -> float:
        values = [getattr(self, m) for m in METRICS]
        return round(sum(values) / len(values), 1)


class PriorVerdict(BaseModel):
    """Judgement on an issue that was open coming into this session."""

    description: str
    status: Status = "unchanged"
    evidence: str = ""

    model_config = ConfigDict(extra="forbid")


class NewIssue(BaseModel):
    """A communication issue newly observed this session."""

    description: str
    category: Category = "general"
    severity: Severity = "medium"

    model_config = ConfigDict(extra="forbid")


class Analysis(BaseModel):
    """The full structured result of one analysis call."""

    scores: Scores = Field(default_factory=Scores)
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    prior_issue_verdicts: list[PriorVerdict] = Field(default_factory=list)
    new_issues: list[NewIssue] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @property
    def overall_score(self) -> float:
        return self.scores.mean()

    def open_issues(self, prior_issues: list[dict]) -> list[dict]:
        """Issues still open after this session.

        Carry forward prior issues judged *unchanged* or *worse* (matched by
        description back to their original category/severity), plus every new
        issue. Prior issues judged *improved* are considered resolved and drop
        off the open list.
        """
        by_desc = {i["description"]: i for i in prior_issues}
        verdicts_by_desc = {verdict.description: verdict for verdict in self.prior_issue_verdicts}
        still_open: list[dict] = []
        # Defensive fallback: even if an Analysis is constructed outside the
        # LLM validation path, an omitted prior verdict must never silently
        # resolve an issue. Omitted issues remain open as "unchanged".
        for description, original in by_desc.items():
            verdict = verdicts_by_desc.get(description)
            if verdict is None or verdict.status in ("unchanged", "worse"):
                still_open.append(dict(original))

        # Preserve a verdict for an unknown issue rather than dropping it.
        for verdict in self.prior_issue_verdicts:
            if verdict.description not in by_desc and verdict.status in ("unchanged", "worse"):
                still_open.append(
                    {"description": verdict.description, "category": "general", "severity": "medium"}
                )
        still_open.extend(issue.model_dump() for issue in self.new_issues)
        return still_open


def validate_llm_payload(payload: object, prior_issues: list[dict]) -> Analysis:
    """Strictly validate one LLM response before it can update learner data.

    ``Analysis`` deliberately has safe defaults for application fallbacks, but
    accepting those defaults for a partial model response would turn missing
    information into misleading scores or accidentally resolve an issue.
    """
    if not isinstance(payload, dict):
        raise ValueError("Analysis response must be a JSON object")

    required_top_level = {
        "scores", "summary", "strengths", "prior_issue_verdicts", "new_issues"
    }
    if set(payload) != required_top_level:
        raise ValueError("Analysis response must contain exactly the required top-level keys")

    scores = payload.get("scores")
    if not isinstance(scores, dict) or set(scores) != set(METRICS):
        raise ValueError("Analysis response must contain all five score metrics")

    result = Analysis.model_validate(payload)
    expected_descriptions = {issue["description"] for issue in prior_issues}
    returned_descriptions = [verdict.description for verdict in result.prior_issue_verdicts]
    if len(returned_descriptions) != len(set(returned_descriptions)):
        raise ValueError("Analysis response contains duplicate prior-issue verdicts")
    if set(returned_descriptions) != expected_descriptions:
        raise ValueError("Analysis response must return one verdict for every prior issue")
    return result
