# ─── agents/base_agent.py ───
"""Abstract base agent for all English Coach agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base class that every agent must extend."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent logic and return updated state."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the agent to its initial state."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
