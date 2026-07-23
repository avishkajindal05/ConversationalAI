# ─── memory/state_manager.py ───
"""Manages SessionState lifecycle: create, update, persist, restore."""

from __future__ import annotations

from .session_state import SessionState


class StateManager:
    """Facade for session state operations."""

    def __init__(self) -> None:
        self._state = SessionState()

    @property
    def state(self) -> SessionState:
        """Return the current session state."""
        return self._state

    def reset(self) -> None:
        """Reset session state to defaults."""
        self._state = SessionState()

    def snapshot(self) -> dict:
        """Return a serialisable snapshot of the current state."""
        return self._state.model_dump()

    def restore(self, data: dict) -> None:
        """Restore session state from a dictionary."""
        self._state = SessionState.model_validate(data)
