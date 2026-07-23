# ─── agents/evaluation/engagement.py ───
"""Engagement evaluation agent.

Average response length and follow-up-question count are computed
deterministically from the transcript; initiative/curiosity/topic
continuity are judged by the evaluation LLM.
"""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.llm.evaluation_model import EvaluationModel
from english_coach.memory.session_state import SessionState

SYSTEM_PROMPT = """You are an expert conversation-engagement evaluator \
reviewing a transcript of a spoken-English practice conversation. Judge \
only the learner's ("user") turns: initiative (do they add new information \
unprompted?), curiosity (do they ask the coach questions?), and topic \
continuity (do they build on previous turns rather than giving one-word \
answers?).

Return STRICT JSON with exactly this shape, no extra commentary:
{
  "score": <integer 0-100>,
  "initiative": "<short note>",
  "curiosity": "<short note>",
  "topic_continuity": "<short note>"
}"""

_FALLBACK = {"score": 50, "initiative": "", "curiosity": "", "topic_continuity": ""}


class EngagementAgent(BaseAgent):
    """Scores how actively the learner drove the conversation."""

    def __init__(self) -> None:
        super().__init__(name="engagement_agent")
        self.model = EvaluationModel()

    def run(self, state: SessionState) -> dict:
        logger.info("EngagementAgent running...")
        user_turns = [
            m.get("content", "")
            for m in state.conversation.messages
            if m.get("role") == "user"
        ]
        word_counts = [len(t.split()) for t in user_turns]
        average_words = sum(word_counts) / len(word_counts) if word_counts else 0.0
        follow_up_questions = sum(t.count("?") for t in user_turns)

        result = self.model.evaluate(SYSTEM_PROMPT, state.evaluation.transcript, _FALLBACK)
        result["average_words"] = round(average_words, 1)
        result["follow_up_questions"] = follow_up_questions
        return {"scores": {"engagement": result}}

    def reset(self) -> None:
        pass
