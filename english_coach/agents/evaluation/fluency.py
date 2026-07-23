# ─── agents/evaluation/fluency.py ───
"""Fluency evaluation agent (text-based proxy; pronunciation is deferred)."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are an expert English fluency evaluator reviewing a \
transcript of a spoken-English practice conversation. Pronunciation and \
audio timing are not available to you, so judge fluency from text alone: \
response completeness, logical flow, naturalness of phrasing, and sentence \
construction in the learner's ("user") turns only.

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "score": <integer 0-100>,
  "completeness": "<short note on whether answers were fully formed>",
  "naturalness": "<short note on how natural the phrasing sounded>",
  "notes": "<one or two sentence overall summary>"
}"""

_FALLBACK = {"score": 50, "completeness": "", "naturalness": "", "notes": ""}


class FluencyAgent(BaseAgent):
    """Scores text-level fluency: completeness, flow, naturalness."""

    def __init__(self) -> None:
        super().__init__(name="fluency_agent")
        self.model = EvaluationModel()

    def run(self, state: SessionState) -> dict:
        logger.info("FluencyAgent running...")
        result = self.model.evaluate(SYSTEM_PROMPT, state.evaluation.transcript, _FALLBACK)
        return {"scores": {"fluency": result}}

    def reset(self) -> None:
        pass
