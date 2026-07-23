# ─── agents/conversation/greeting.py ───
"""Greeting agent: sets the opening context for a new session."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.memory.session_state import SessionState


class GreetingAgent(BaseAgent):
    """Prepares the opening instructions the Conversation Agent will speak.

    Runs once, at the very start of a session (turn_count == 0). It never
    talks to the learner directly - it hands off instructions that the
    Conversation Agent turns into a natural greeting.
    """

    def __init__(self) -> None:
        super().__init__(name="greeting_agent")

    def run(self, state: SessionState) -> SessionState:
        logger.info("GreetingAgent running...")
        profile = state.learner_profile

        topic = profile.recommended_topics[0] if profile.recommended_topics else "everyday life"
        goal = profile.learning_goal or "practising general conversational fluency"

        state.conversation.topic = topic
        state.session.status = "active"
        state.conversation.context["opening_instructions"] = (
            f"This is session #{profile.session_count + 1} for this learner "
            f"(estimated level: {profile.estimated_level}). "
            f"Warmly greet them, briefly state today's session goal "
            f"('{goal}'), and ask an easy opening question about the topic "
            f"'{topic}' to get them talking."
        )
        return state

    def reset(self) -> None:
        pass
