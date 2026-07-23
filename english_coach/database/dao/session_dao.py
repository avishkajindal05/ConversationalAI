# ─── database/dao/session_dao.py ───
"""Data Access Object for conversation sessions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from english_coach.core.time_utils import utcnow
from english_coach.database.models import MessageRecord, SessionRecord


class SessionDAO:
    """CRUD operations for conversation session records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, data: dict) -> SessionRecord:
        """Create a new session record."""
        record = SessionRecord(
            session_id=data["session_id"],
            user_id=data["user_id"],
            started_at=data.get("started_at", utcnow()),
            status=data.get("status", "active"),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def get_by_id(self, session_id: str) -> SessionRecord | None:
        """Retrieve a session by its ID."""
        return self._db.get(SessionRecord, session_id)

    def list_all(self) -> list[SessionRecord]:
        """List all sessions."""
        return list(self._db.query(SessionRecord).all())

    def list_by_user(self, user_id: str) -> list[SessionRecord]:
        """List all sessions for a given user, most recent first."""
        return (
            self._db.query(SessionRecord)
            .filter(SessionRecord.user_id == user_id)
            .order_by(SessionRecord.started_at.desc())
            .all()
        )

    def end_session(self, session_id: str, overall_score: float = 0.0) -> SessionRecord | None:
        """Mark a session as ended and record its duration/score."""
        record = self.get_by_id(session_id)
        if record is None:
            return None
        record.ended_at = utcnow()
        record.duration = (record.ended_at - record.started_at).total_seconds()
        record.overall_score = overall_score
        record.status = "completed"
        self._db.commit()
        self._db.refresh(record)
        return record

    def add_message(self, session_id: str, speaker: str, text: str) -> MessageRecord:
        """Append a message to a session's transcript."""
        message = MessageRecord(session_id=session_id, speaker=speaker, text=text)
        self._db.add(message)
        self._db.commit()
        self._db.refresh(message)
        return message

    def get_messages(self, session_id: str) -> list[MessageRecord]:
        """Return the full transcript for a session, in order."""
        return (
            self._db.query(MessageRecord)
            .filter(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.timestamp)
            .all()
        )

    def delete(self, session_id: str) -> None:
        """Delete a session by its ID."""
        record = self.get_by_id(session_id)
        if record is not None:
            self._db.delete(record)
            self._db.commit()
