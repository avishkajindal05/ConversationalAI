# ─── agents/evaluation/confidence.py ───
"""Confidence evaluation agent.

Produces a communication-confidence estimate from linguistic signals in
the transcript, not a psychological assessment.
"""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are an expert evaluator of communication confidence, \
reviewing a transcript of a spoken-English practice conversation. Judge \
only the learner's ("user") turns for: hedging language ("maybe", "I \
think", "sorry", "I'm not sure"), self-corrections, uncertainty phrases, \
and hesitation patterns inferred from the text. Produce a communication \
confidence estimate, not a psychological assessment.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "score": <integer 0-100>,
  "hedging_frequency": <float 0-1, share of learner turns containing hedging language>,
  "notes": "<one or two sentence summary>"
}"""

_FALLBACK = {"score": 50, "hedging_frequency": 0.0, "notes": ""}


class ConfidenceAgent(BaseAgent):
    """Scores communication confidence from hedging/hesitation signals."""

    def __init__(self) -> None:
        super().__init__(name="confidence_agent")
        self.model = EvaluationModel()

    def run(self, state: SessionState) -> dict:
        logger.info("ConfidenceAgent running...")
        result = self.model.evaluate(SYSTEM_PROMPT, state.evaluation.transcript, _FALLBACK)
        return {"scores": {"confidence": result}}

    def reset(self) -> None:
        pass
