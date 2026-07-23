# ─── tests/integration/test_conversation_graph.py ───
"""Conversation graph execution with a mocked LLM (no Ollama, no DB writes)."""

from __future__ import annotations

from unittest.mock import patch

from english_coach.graphs.conversation_graph import ConversationGraph
from english_coach.llm.conversation_model import ConversationModel
from english_coach.memory.session_state import SessionState


def _run_turn(state: SessionState) -> SessionState:
    with patch.object(ConversationModel, "respond", return_value="Hello, mock reply!"):
        graph = ConversationGraph().build_graph()
        result = graph.invoke(state)
    return SessionState.model_validate(result)


def test_first_turn_runs_greeting_and_appends_reply():
    state = SessionState()  # session_id="" so MemoryManager skips DB writes
    state.learner_profile.estimated_level = "A2"
    state.learner_profile.recommended_topics = ["Travel"]

    result = _run_turn(state)

    # Greeting agent set the opening instructions and topic.
    assert result.conversation.topic == "Travel"
    assert "opening_instructions" in result.conversation.context
    # Difficulty planner injected level guidance.
    assert result.conversation.context["difficulty"] == "A2"
    # Conversation agent appended the assistant reply.
    assert result.conversation.messages[-1] == {
        "role": "assistant",
        "content": "Hello, mock reply!",
    }
    # Memory manager advanced the turn counter.
    assert result.conversation.turn_count == 1


def test_later_turn_skips_greeting():
    state = SessionState()
    state.conversation.turn_count = 3
    state.conversation.messages = [{"role": "user", "content": "How are you?"}]

    result = _run_turn(state)

    # No greeting on a later turn.
    assert "opening_instructions" not in result.conversation.context
    assert result.conversation.turn_count == 4
    assert result.conversation.messages[-1]["role"] == "assistant"
