# ─── memory/session_state.py ───
"""Central session state model.

Uses Pydantic v2 with Field(default_factory=...) for all mutable defaults.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field


def merge_scores(existing: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Reducer for the top-level `scores` channel.

    The five scoring agents run in parallel (fan-out) and each returns a
    partial ``{"scores": {"<agent>": ...}}`` update. LangGraph applies this
    reducer to merge those concurrent writes into one dict instead of
    raising InvalidUpdateError.
    """
    merged = dict(existing or {})
    merged.update(update or {})
    return merged


# ── Nested sub-models ────────────────────────────────────────────────────


class UserState(BaseModel):
    """Current user identity information."""
    user_id: str = ""
    username: str = ""


class LearnerProfileState(BaseModel):
    """Snapshot of the learner profile within the session."""
    level: str = "beginner"
    native_language: str = ""
    goals: list[str] = Field(default_factory=list)
    estimated_level: str = "A1"
    learning_goal: str = ""
    recommended_topics: list[str] = Field(default_factory=list)
    grammar_weaknesses: list[str] = Field(default_factory=list)
    vocabulary_weaknesses: list[str] = Field(default_factory=list)
    session_count: int = 0
    previous_overall_score: float = 0.0


class SessionInfo(BaseModel):
    """Metadata about the running session."""
    session_id: str = ""
    started_at: datetime | None = None
    ended_at: datetime | None = None
    status: str = "idle"


class ConversationState(BaseModel):
    """State of the ongoing conversation."""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    turn_count: int = 0
    topic: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class AudioState(BaseModel):
    """State of audio input/output."""
    last_audio_path: str = ""
    last_transcript: str = ""
    last_tts_path: str = ""


class EvaluationState(BaseModel):
    """State of the evaluation pass.

    Note: per-agent scores live in the top-level ``SessionState.scores``
    channel (which carries a reducer for parallel fan-in), not here.
    """
    transcript: str = ""
    recommendation: dict[str, Any] = Field(default_factory=dict)
    feedback: str = ""
    evaluated: bool = False


class ReportState(BaseModel):
    """State of report generation."""
    report_id: str = ""
    generated: bool = False
    path: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class RuntimeState(BaseModel):
    """Transient runtime information."""
    loaded_model: str = ""
    active_graph: str = ""
    current_agent: str = ""
    execution_time: float = 0.0
    errors: list[str] = Field(default_factory=list)


class MetadataState(BaseModel):
    """Arbitrary metadata bag."""
    extra: dict[str, Any] = Field(default_factory=dict)


# ── Top-level SessionState ───────────────────────────────────────────────


class SessionState(BaseModel):
    """Root session state aggregating every sub-state."""
    user: UserState = Field(default_factory=UserState)
    learner_profile: LearnerProfileState = Field(default_factory=LearnerProfileState)
    session: SessionInfo = Field(default_factory=SessionInfo)
    conversation: ConversationState = Field(default_factory=ConversationState)
    audio: AudioState = Field(default_factory=AudioState)
    # Top-level so the parallel scoring agents can fan-in via merge_scores.
    scores: Annotated[dict[str, Any], merge_scores] = Field(default_factory=dict)
    evaluation: EvaluationState = Field(default_factory=EvaluationState)
    report: ReportState = Field(default_factory=ReportState)
    runtime: RuntimeState = Field(default_factory=RuntimeState)
    metadata: MetadataState = Field(default_factory=MetadataState)
