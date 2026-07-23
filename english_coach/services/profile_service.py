# ─── services/profile_service.py ───
"""Service that loads and persists LearnerProfile objects via LearnerDAO."""

from __future__ import annotations

from english_coach.core.logger import logger
from english_coach.database.connection import SessionLocal
from english_coach.database.dao.learner_dao import LearnerDAO
from english_coach.memory.learner_profile import LearnerProfile


class ProfileService:
    """Facade over LearnerDAO that speaks in LearnerProfile pydantic objects."""

    def load(self, user_id: str) -> LearnerProfile:
        """Load a learner's profile, creating a fresh one if none exists."""
        db = SessionLocal()
        try:
            dao = LearnerDAO(db)
            dao.get_or_create_user(user_id)
            record = dao.get_by_id(user_id)
            if record is None:
                logger.info("No profile found for %s, creating default.", user_id)
                profile = LearnerProfile(user_id=user_id)
                dao.create(profile.to_dict())
                return profile
            return LearnerProfile.from_record(record)
        finally:
            db.close()

    def save(self, profile: LearnerProfile) -> None:
        """Persist a learner profile, updating the existing row if present."""
        db = SessionLocal()
        try:
            dao = LearnerDAO(db)
            dao.get_or_create_user(profile.user_id)
            dao.update(profile.user_id, profile.to_dict())
            logger.info("Saved learner profile for %s", profile.user_id)
        finally:
            db.close()


profile_service = ProfileService()
