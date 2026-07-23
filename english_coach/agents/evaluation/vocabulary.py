# ─── agents/evaluation/vocabulary.py ───
"""Vocabulary evaluation agent."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are an expert English vocabulary evaluator reviewing \
a transcript of a spoken-English practice conversation. Judge only the \
learner's ("user") turns.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "score": <integer 0-100>,
  "lexical_diversity": <float 0-1, unique words / total words used by the learner>,
  "repeated_words": ["word", ...],
  "strengths": ["topic or word-family the learner used well", ...],
  "weaknesses": ["topic or word-family the learner struggled with", ...],
  "suggested_replacements": ["<overused word> -> <better alternative>", ...]
}"""

_FALLBACK = {
    "score": 50,
    "lexical_diversity": 0.0,
    "repeated_words": [],
    "strengths": [],
    "weaknesses": [],
    "suggested_replacements": [],
}


class VocabularyAgent(BaseAgent):
    """Scores lexical range and diversity."""

    def __init__(self) -> None:
        super().__init__(name="vocabulary_agent")
        self.model = EvaluationModel()

    def run(self, state: SessionState) -> dict:
        logger.info("VocabularyAgent running...")
        result = self.model.evaluate(SYSTEM_PROMPT, state.evaluation.transcript, _FALLBACK)
        return {"scores": {"vocabulary": result}}

    def reset(self) -> None:
        pass
