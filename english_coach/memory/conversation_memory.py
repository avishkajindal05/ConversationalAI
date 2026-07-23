# ─── memory/conversation_memory.py ───
"""In-memory conversation history buffer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConversationMemory(BaseModel):
    """Stores the rolling conversation history for one session."""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    max_turns: int = 50

    def add_message(self, role: str, content: str) -> None:
        """Append a message and trim if over max_turns."""
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-self.max_turns * 2 :]

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages.clear()

    def to_langchain_messages(self) -> list[dict[str, str]]:
        """Return messages in LangChain-compatible format."""
        return list(self.messages)
