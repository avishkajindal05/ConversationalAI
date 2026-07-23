# ─── agents/evaluation/recommendation.py ───
"""Learning recommendation agent: turns scores into concrete next steps.

The next-session goal is derived deterministically in Python from the
scores (cheap, explainable, no tokens). The LLM is asked only to write the
homework / exercises / topics for that goal, from the scores alone — it
never re-reads the transcript.
"""

from __future__ import annotations

import json
from typing import Any

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.core.settings import settings
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

# First failing dimension (score < threshold) decides the focus goal.
_GOAL_RULES = [
    ("grammar", 60, "Practice past tense narration with correct verb forms"),
    ("vocabulary", 60, "Expand everyday vocabulary and word variety"),
    ("fluency", 60, "Improve speaking fluency and sentence flow"),
    ("confidence", 60, "Build speaking confidence and reduce hesitation"),
    ("engagement", 60, "Take more initiative and ask follow-up questions"),
]
_DEFAULT_GOAL = "Keep building overall conversational fluency"

SYSTEM_PROMPT = """You are an English learning coach. Given the learner's \
next goal and a short JSON summary of their scores, write practice material \
for that goal. Do not restate the scores.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "homework": "<one concrete take-home task, e.g. 'Describe yesterday for five minutes.'>",
  "exercises": ["<short drill>", "<short drill>"],
  "conversation_topics": ["<topic to explore next session>", ...]
}"""

_FALLBACK = {
    "homework": "Talk about your day out loud for five minutes.",
    "exercises": [],
    "conversation_topics": [],
}


def derive_goal(scores: dict[str, Any]) -> str:
    """Pick the next-session goal from the first weak dimension."""
    for key, threshold, goal in _GOAL_RULES:
        value = scores.get(key, {}).get("score")
        if isinstance(value, (int, float)) and value < threshold:
            return goal
    return _DEFAULT_GOAL


class RecommendationAgent(BaseAgent):
    """Generates homework, drills, and the next-session goal from the scores."""

    def __init__(self) -> None:
        super().__init__(name="recommendation_agent")
        # The next-session goal is derived in Python (see derive_goal), so this
        # agent is now writing, not reasoning — it runs on the lighter scoring
        # model like the Report agent.
        self.model = EvaluationModel(settings.scoring_model)

    def run(self, state: SessionState) -> SessionState:
        logger.info("RecommendationAgent running...")
        scores = state.scores
        goal = derive_goal(scores)

        # Compact input: the goal plus just the numeric scores, no transcript.
        score_digest = {k: v.get("score") for k, v in scores.items()}
        content = (
            f"Next goal: {goal}\n"
            f"Scores: {json.dumps(score_digest)}"
        )
        result = self.model.evaluate(SYSTEM_PROMPT, content, _FALLBACK)
        result["next_session_goal"] = goal
        state.evaluation.recommendation = result
        return state

    def reset(self) -> None:
        pass
