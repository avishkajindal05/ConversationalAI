# ─── agents/evaluation/grammar.py ───
"""Grammar evaluation agent.

Scoring uses a strict two-step prompt: the model must first list *every* error
and only then score against an explicit rubric. A cold "give a score" prompt
was far too lenient for a coaching product (it rated an error-riddled learner
transcript 82/100; the two-step prompt rates the same text ~22 and clean text
~92). When LanguageTool is available its verified corrections are merged in;
that add-on is optional and never affects the score (see grammar_tool.py).
"""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.agents.evaluation.grammar_tool import verified_corrections
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are a STRICT English grammar examiner assessing a language \
learner. Judge ONLY the learner's ("user") turns; the coach's ("assistant") \
turns are context only.

Work in two steps:
1. Find EVERY grammatical error in the learner's turns: verb tense, subject-verb \
agreement, articles (a/an/the), prepositions, plurals, word form (e.g. "excited" \
vs "exciting"), and sentence structure. This is a learner — be thorough and do \
not overlook errors.
2. Assign a score from 0 to 100 using this rubric, based on how many of the \
learner's turns contain errors:
   90-100: essentially error-free, native-like
   75-89 : only minor slips, meaning always clear
   60-74 : several noticeable errors but still understandable
   40-59 : frequent errors, most sentences affected
   below 40: errors in nearly every clause

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
        transcript = state.evaluation.transcript
        result = self.model.evaluate(SYSTEM_PROMPT, transcript, _FALLBACK)

        # Optionally fold in LanguageTool's verified corrections (offline,
        # best-effort). Never changes the score; just enriches the feedback.
        for correction in verified_corrections(transcript):
            if correction not in result.setdefault("corrections", []):
                result["corrections"].append(correction)

        # Partial update: parallel-safe fan-in via the scores reducer.
        return {"scores": {"grammar": result}}

    def reset(self) -> None:
        pass
