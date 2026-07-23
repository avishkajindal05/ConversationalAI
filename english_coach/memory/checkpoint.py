# ─── memory/checkpoint.py ───
"""Checkpoint model for saving/restoring graph state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from english_coach.core.time_utils import utcnow


class Checkpoint(BaseModel):
    """Serialisable snapshot of graph execution state."""
    checkpoint_id: str = ""
    session_id: str = ""
    graph_name: str = ""
    node_name: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
