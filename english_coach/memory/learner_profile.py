# ─── memory/learner_profile.py ───
"""Learner profile model and helpers.

This is the long-term, cross-session model of a learner. It is loaded at the
start of every session (by the Greeting Agent / Difficulty Planner) and
rewritten at the end of every session once the Evaluation Graph finishes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

DEFAULT_TOPICS = ["Daily life", "Travel", "Technology"]


class GrammarProfile(BaseModel):
    score: float = 0.0
    common_errors: list[str] = Field(default_factory=list)


class VocabularyProfile(BaseModel):
    score: float = 0.0
    lexical_diversity: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class EngagementProfile(BaseModel):
    score: float = 0.0
    average_words: float = 0.0
    follow_up_questions: int = 0


class ConfidenceProfile(BaseModel):
    score: float = 0.0
    hedging_frequency: float = 0.0
    notes: str = ""


class RecommendationProfile(BaseModel):
    next_session_goal: str = ""
    homework: str = ""
    exercises: list[str] = Field(default_factory=list)


class LearnerProfile(BaseModel):
    """Persistent learner profile stored across sessions."""

    user_id: str = ""
    estimated_level: str = "A1"
    overall_score: float = 0.0
    learning_goal: str = "Improve general conversational fluency"

    grammar: GrammarProfile = Field(default_factory=GrammarProfile)
    vocabulary: VocabularyProfile = Field(default_factory=VocabularyProfile)
    engagement: EngagementProfile = Field(default_factory=EngagementProfile)
    confidence: ConfidenceProfile = Field(default_factory=ConfidenceProfile)
    recommendation: RecommendationProfile = Field(default_factory=RecommendationProfile)

    recommended_topics: list[str] = Field(default_factory=lambda: list(DEFAULT_TOPICS))
    session_history: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        """Flatten to the dict shape expected by LearnerDAO."""
        return {
            "user_id": self.user_id,
            "estimated_level": self.estimated_level,
            "overall_score": self.overall_score,
            "learning_goal": self.learning_goal,
            "grammar": self.grammar.model_dump(),
            "vocabulary": self.vocabulary.model_dump(),
            "engagement": self.engagement.model_dump(),
            "confidence": self.confidence.model_dump(),
            "recommendation": self.recommendation.model_dump(),
            "recommended_topics": self.recommended_topics,
            "session_history": self.session_history,
        }

    @classmethod
    def from_record(cls, record: object) -> "LearnerProfile":
        """Build a LearnerProfile from a LearnerProfileRecord ORM row."""
        return cls(
            user_id=record.user_id,
            estimated_level=record.estimated_level,
            overall_score=record.overall_score,
            learning_goal=record.learning_goal,
            grammar=GrammarProfile(**(record.grammar_json or {})),
            vocabulary=VocabularyProfile(**(record.vocabulary_json or {})),
            engagement=EngagementProfile(**(record.engagement_json or {})),
            confidence=ConfidenceProfile(**(record.confidence_json or {})),
            recommendation=RecommendationProfile(**(record.recommendation_json or {})),
            recommended_topics=list(record.recommended_topics_json or DEFAULT_TOPICS),
            session_history=list(record.session_history_json or []),
        )
