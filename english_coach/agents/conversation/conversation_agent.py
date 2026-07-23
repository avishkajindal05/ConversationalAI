# ─── agents/conversation/conversation_agent.py ───
"""Conversation agent implementation."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.memory.session_state import SessionState
from english_coach.llm.conversation_model import ConversationModel
from english_coach.core.logger import logger


class ConversationAgent(BaseAgent):
    """Agent responsible for handling conversational turns."""

    def __init__(self) -> None:
        super().__init__(name="conversation_agent")
        self.model = ConversationModel()

    def run(self, state: SessionState) -> SessionState:
        """Process the conversation state and generate a response."""
        logger.info("ConversationAgent running...")

        # The user's latest message should already be in state.conversation.messages
        # We just need to pass the conversation history to the model
        messages = state.conversation.messages

        # Combine planner guidance with the one-time opening instructions
        # (only relevant for the very first turn of a session).
        context = state.conversation.context
        parts = []
        if state.conversation.turn_count == 0 and context.get("opening_instructions"):
            parts.append(context["opening_instructions"])
        if context.get("difficulty_instructions"):
            parts.append(context["difficulty_instructions"])
        extra_instructions = "\n".join(parts)

        # Invoke the LLM
        response_text = self.model.respond(messages, extra_instructions=extra_instructions)
        
        # Append the AI response to the state
        state.conversation.messages.append({
            "role": "assistant",
            "content": response_text
        })
        
        logger.info("ConversationAgent generated response.")
        return state

    def reset(self) -> None:
        """Reset agent (no-op for stateless agent)."""
        pass
