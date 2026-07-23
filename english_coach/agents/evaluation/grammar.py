# ─── agents/evaluation/grammar.py ───
"""Grammar evaluation agent."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are an expert English grammar evaluator reviewing a \
transcript of a spoken-English practice conversation. Judge only the \
learner's ("user") turns; the coach's ("assistant") turns are context only.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "score": <integer 0-100>,
  "common_errors": ["short label", ...],
  "examples": ["<verbatim learner sentence with the error>", ...],
  "corrections": ["<corrected version of that sentence>", ...]
}"""

_FALLBACK = {"score": 50, "common_errors": [], "examples": [], "corrections": []}


class GrammarAgent(BaseAgent):
    """Scores grammatical accuracy and lists recurring mistakes."""

    def __init__(self) -> None:
        super().__init__(name="grammar_agent")
        self.model = EvaluationModel()

    def run(self, state: SessionState) -> dict:
        logger.info("GrammarAgent running...")
        result = self.model.evaluate(SYSTEM_PROMPT, state.evaluation.transcript, _FALLBACK)
        # Partial update: parallel-safe fan-in via the scores reducer.
        return {"scores": {"grammar": result}}

    def reset(self) -> None:
        pass
