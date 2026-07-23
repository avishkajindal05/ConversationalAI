# ─── database/models.py ───
"""SQLAlchemy ORM table definitions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from english_coach.core.time_utils import utcnow
from english_coach.database.connection import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    sessions: Mapped[list["SessionRecord"]] = relationship(back_populates="user")
    profile: Mapped["LearnerProfileRecord | None"] = relationship(
        back_populates="user", uselist=False
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="active")

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["MessageRecord"]] = relationship(
        back_populates="session", order_by="MessageRecord.timestamp"
    )
    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="session")


class MessageRecord(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"))
    speaker: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    session: Mapped["SessionRecord"] = relationship(back_populates="messages")


class LearnerProfileRecord(Base):
    __tablename__ = "learner_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    estimated_level: Mapped[str] = mapped_column(String, default="A1")
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    learning_goal: Mapped[str] = mapped_column(String, default="")
    grammar_json: Mapped[dict] = mapped_column(JSON, default=dict)
    vocabulary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    engagement_json: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation_json: Mapped[dict] = mapped_column(JSON, default=dict)
    recommended_topics_json: Mapped[list] = mapped_column(JSON, default=list)
    session_history_json: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="profile")


class ReportRecord(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.session_id"))
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    report_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    session: Mapped["SessionRecord"] = relationship(back_populates="reports")


def init_db() -> None:
    """Create all tables if they do not already exist."""
    from english_coach.database.connection import engine

    Base.metadata.create_all(bind=engine)
