# ─── database/dao/learner_dao.py ───
"""Data Access Object for learner profiles."""

from __future__ import annotations

from sqlalchemy.orm import Session

from english_coach.core.time_utils import utcnow
from english_coach.database.models import LearnerProfileRecord, User


class LearnerDAO:
    """CRUD operations for learner profile records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create_user(self, user_id: str, name: str = "") -> User:
        """Fetch a user row, creating it if it does not exist."""
        user = self._db.get(User, user_id)
        if user is None:
            user = User(user_id=user_id, name=name or user_id)
            self._db.add(user)
            self._db.commit()
            self._db.refresh(user)
        return user

    def create(self, data: dict) -> LearnerProfileRecord:
        """Create a new learner profile record."""
        self.get_or_create_user(data["user_id"])
        record = LearnerProfileRecord(
            user_id=data["user_id"],
            estimated_level=data.get("estimated_level", "A1"),
            overall_score=data.get("overall_score", 0.0),
            learning_goal=data.get("learning_goal", ""),
            grammar_json=data.get("grammar", {}),
            vocabulary_json=data.get("vocabulary", {}),
            engagement_json=data.get("engagement", {}),
            confidence_json=data.get("confidence", {}),
            recommendation_json=data.get("recommendation", {}),
            recommended_topics_json=data.get("recommended_topics", []),
            session_history_json=data.get("session_history", []),
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def get_by_id(self, learner_id: str) -> LearnerProfileRecord | None:
        """Retrieve a learner profile by user ID."""
        return self._db.get(LearnerProfileRecord, learner_id)

    def update(self, learner_id: str, data: dict) -> LearnerProfileRecord | None:
        """Update a learner profile record, creating it if missing."""
        record = self.get_by_id(learner_id)
        if record is None:
            return self.create({**data, "user_id": learner_id})

        field_map = {
            "estimated_level": "estimated_level",
            "overall_score": "overall_score",
            "learning_goal": "learning_goal",
            "grammar": "grammar_json",
            "vocabulary": "vocabulary_json",
            "engagement": "engagement_json",
            "confidence": "confidence_json",
            "recommendation": "recommendation_json",
            "recommended_topics": "recommended_topics_json",
            "session_history": "session_history_json",
        }
        for key, column in field_map.items():
            if key in data:
                setattr(record, column, data[key])
        record.updated_at = utcnow()

        self._db.commit()
        self._db.refresh(record)
        return record

    def delete(self, learner_id: str) -> None:
        """Delete a learner profile record."""
        record = self.get_by_id(learner_id)
        if record is not None:
            self._db.delete(record)
            self._db.commit()
