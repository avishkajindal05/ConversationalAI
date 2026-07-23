# ─── agents/evaluation/report.py ───
"""Report generator: aggregates every evaluation agent's output."""

from __future__ import annotations

import json

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.constants import REPORT_SUMMARY_MAX_TOKENS
from english_coach.core.logger import logger
from english_coach.core.settings import settings
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

# Report generation is writing, not reasoning, so it runs on the lighter
# scoring model with a capped output length rather than the reasoning model.
SYSTEM_PROMPT = """You are writing the closing summary of an English \
practice session. You are given the learner's per-skill scores (0-100), \
their next goal, and their previous overall score. Write an encouraging, \
concrete summary. Do not invent scores.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "summary": "<two or three encouraging sentences about the session>",
  "strengths": ["<short strength>", ...],
  "weaknesses": ["<short weakness>", ...],
  "progress": "<one sentence comparing this session to the previous overall score>"
}"""

_FALLBACK = {"summary": "", "strengths": [], "weaknesses": [], "progress": ""}

# Weighted so grammar/vocabulary (the most reliable text-only signals) count
# more than the softer engagement/confidence estimates.
_SCORE_WEIGHTS = {
    "grammar": 0.3,
    "vocabulary": 0.25,
    "fluency": 0.2,
    "engagement": 0.15,
    "confidence": 0.1,
}


class ReportAgent(BaseAgent):
    """Combines every evaluation agent's output into the final report."""

    def __init__(self) -> None:
        super().__init__(name="report_agent")
        self.model = EvaluationModel(
            settings.scoring_model, num_predict=REPORT_SUMMARY_MAX_TOKENS
        )

    def run(self, state: SessionState) -> SessionState:
        logger.info("ReportAgent running...")
        scores = state.scores
        overall_score = self._weighted_overall(scores)

        # Compact digest: just the numbers + the goal, not the full nested
        # score dicts (which carry examples/corrections that bloat the prompt).
        digest = {
            "scores": {k: v.get("score") for k, v in scores.items()},
            "next_goal": state.evaluation.recommendation.get("next_session_goal", ""),
            "previous_overall_score": state.learner_profile.previous_overall_score,
            "this_overall_score": overall_score,
        }
        narrative = self.model.evaluate(SYSTEM_PROMPT, json.dumps(digest), _FALLBACK)

        state.report.data = {
            "overall_score": overall_score,
            "summary": narrative.get("summary", ""),
            "strengths": narrative.get("strengths", []),
            "weaknesses": narrative.get("weaknesses", []),
            "progress": narrative.get("progress", ""),
            "scores": scores,
            "recommendation": state.evaluation.recommendation,
        }
        state.report.generated = True
        state.evaluation.evaluated = True
        return state

    @staticmethod
    def _weighted_overall(scores: dict) -> float:
        total_weight = 0.0
        total = 0.0
        for key, weight in _SCORE_WEIGHTS.items():
            value = scores.get(key, {}).get("score")
            if isinstance(value, (int, float)):
                total += value * weight
                total_weight += weight
        return round(total / total_weight, 1) if total_weight else 0.0

    def reset(self) -> None:
        pass
