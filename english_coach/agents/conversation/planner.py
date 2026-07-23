# ─── agents/conversation/planner.py ───
"""Difficulty planner: decides CEFR-appropriate vocabulary/grammar/topic depth."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.memory.session_state import SessionState

_LEVEL_GUIDANCE = {
    "A1": (
        "Use very simple, high-frequency vocabulary and short present-tense "
        "sentences. Ask only one easy question at a time."
    ),
    "A2": (
        "Use simple everyday vocabulary and basic past/future tense. "
        "Keep follow-up questions light and concrete."
    ),
    "B1": (
        "Use moderately varied vocabulary and mixed tenses. Ask one "
        "follow-up question per turn to encourage elaboration."
    ),
    "B2": (
        "Use richer vocabulary and occasional idioms. Encourage "
        "opinion-based answers and ask deeper follow-up questions."
    ),
    "C1": (
        "Use advanced vocabulary and nuanced grammar. Challenge the learner "
        "with abstract, opinion-driven questions and push for detail."
    ),
}
_DEFAULT_LEVEL = "A1"


class DifficultyPlanner(BaseAgent):
    """Turns the learner's CEFR level and weak spots into LLM guidance."""

    def __init__(self) -> None:
        super().__init__(name="difficulty_planner")

    def run(self, state: SessionState) -> SessionState:
        logger.info("DifficultyPlanner running...")
        profile = state.learner_profile
        level = profile.estimated_level or _DEFAULT_LEVEL
        guidance = _LEVEL_GUIDANCE.get(level, _LEVEL_GUIDANCE[_DEFAULT_LEVEL])

        focus = ""
        if profile.grammar_weaknesses:
            targets = ", ".join(profile.grammar_weaknesses[:2])
            focus = f" Naturally create opportunities to practice: {targets}."

        state.conversation.context["difficulty_instructions"] = (
            f"Difficulty guidance ({level}): {guidance}{focus}"
        )
        state.conversation.context["difficulty"] = level
        return state

    def reset(self) -> None:
        pass
