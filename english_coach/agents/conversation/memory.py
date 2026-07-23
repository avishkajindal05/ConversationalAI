# ─── agents/conversation/memory.py ───
"""Memory manager: persists the transcript and advances turn state."""

from __future__ import annotations

from english_coach.agents.base_agent import BaseAgent
from english_coach.core.logger import logger
from english_coach.database.connection import SessionLocal
from english_coach.database.dao.session_dao import SessionDAO
from english_coach.memory.session_state import SessionState


class MemoryManager(BaseAgent):
    """Writes new turns to SQLite and advances the session's turn counter.

    The database is persistence, not the source of truth for an active
    session - SessionState (held in memory for the session's lifetime) is
    the source of truth while the conversation is running.
    """

    def __init__(self) -> None:
        super().__init__(name="memory_manager")

    def run(self, state: SessionState) -> SessionState:
        logger.info("MemoryManager running...")
        session_id = state.session.session_id
        messages = state.conversation.messages
        persisted = state.conversation.context.get("_persisted_count", 0)

        if session_id and len(messages) > persisted:
            db = SessionLocal()
            try:
                dao = SessionDAO(db)
                for msg in messages[persisted:]:
                    dao.add_message(
                        session_id,
                        msg.get("role", "user"),
                        msg.get("content", ""),
                    )
            finally:
                db.close()
            state.conversation.context["_persisted_count"] = len(messages)

        state.conversation.turn_count += 1
        return state

    def reset(self) -> None:
        pass
