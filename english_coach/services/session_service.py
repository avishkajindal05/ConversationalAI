# ─── services/session_service.py ───
"""Orchestrates session lifecycle: start, per-turn chat, and end-of-session
evaluation. Keeps FastAPI route handlers thin.

SessionState lives in memory for the lifetime of an active session (source
of truth); SQLite is the persistence layer for transcripts, sessions, and
reports.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from english_coach.core.logger import logger
from english_coach.core.time_utils import utcnow
from english_coach.database.connection import SessionLocal
from english_coach.database.dao.report_dao import ReportDAO
from english_coach.database.dao.session_dao import SessionDAO
from english_coach.graphs.conversation_graph import ConversationGraph
from english_coach.graphs.evaluation_graph import EvaluationGraph
from english_coach.memory.learner_profile import (
    ConfidenceProfile,
    EngagementProfile,
    GrammarProfile,
    RecommendationProfile,
    VocabularyProfile,
)
from english_coach.memory.session_state import SessionState
from english_coach.services.profile_service import profile_service

_CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

# Human-readable progress labels for the streaming end-of-session endpoint.
_NODE_LABELS = {
    "grammar_node": "Grammar analysed",
    "vocabulary_node": "Vocabulary analysed",
    "fluency_node": "Fluency analysed",
    "engagement_node": "Engagement analysed",
    "confidence_node": "Confidence analysed",
    "recommendation_node": "Recommendations generated",
    "report_node": "Report written",
}


def _advance_level(current: str, overall_score: float) -> str:
    """Bump the learner's CEFR level by one step on a strong session."""
    if overall_score < 85 or current not in _CEFR_ORDER:
        return current
    index = _CEFR_ORDER.index(current)
    return _CEFR_ORDER[min(index + 1, len(_CEFR_ORDER) - 1)]


class SessionService:
    """In-memory registry of active sessions plus graph orchestration."""

    def __init__(self) -> None:
        self._states: dict[str, SessionState] = {}
        self.conversation_graph = ConversationGraph().build_graph()
        self.evaluation_graph = EvaluationGraph().build_graph()

    def start_session(self, user_id: str) -> dict:
        """Create a session, load the learner profile, and run the opening turn."""
        profile = profile_service.load(user_id)
        session_id = str(uuid.uuid4())

        db = SessionLocal()
        try:
            SessionDAO(db).create({"session_id": session_id, "user_id": user_id})
        finally:
            db.close()

        state = SessionState()
        state.user.user_id = user_id
        state.session.session_id = session_id
        state.session.started_at = utcnow()
        state.session.status = "active"
        state.learner_profile.estimated_level = profile.estimated_level
        state.learner_profile.learning_goal = profile.learning_goal
        state.learner_profile.recommended_topics = list(profile.recommended_topics)
        state.learner_profile.grammar_weaknesses = list(profile.grammar.common_errors)
        state.learner_profile.vocabulary_weaknesses = list(profile.vocabulary.weaknesses)
        state.learner_profile.session_count = len(profile.session_history)
        state.learner_profile.previous_overall_score = profile.overall_score

        result_state = self._run_conversation_turn(state)
        self._states[session_id] = result_state

        greeting = ""
        if result_state.conversation.messages:
            greeting = result_state.conversation.messages[-1]["content"]

        return {
            "session_id": session_id,
            "message": greeting,
            "difficulty": result_state.conversation.context.get("difficulty", ""),
        }

    def send_message(self, session_id: str, message: str) -> str:
        """Append a learner message and run one conversation-graph turn."""
        state = self._get_state(session_id)
        state.conversation.messages.append({"role": "user", "content": message})
        result_state = self._run_conversation_turn(state)
        self._states[session_id] = result_state
        return result_state.conversation.messages[-1]["content"]

    def end_session(self, session_id: str) -> dict:
        """Run the evaluation graph, persist the report, and update the profile."""
        state = self._get_state(session_id)
        state.evaluation.transcript = self._build_transcript(state)

        result_dict = self.evaluation_graph.invoke(state)
        result_state = SessionState.model_validate(result_dict)
        return self._finalize(session_id, result_state)

    def end_session_stream(self, session_id: str) -> Iterator[dict]:
        """Streaming variant of end_session.

        Yields ``{"type": "progress", ...}`` events as each evaluation node
        finishes, then a final ``{"type": "report", "report": {...}}`` event.
        Lets the frontend show staged progress during the long evaluation.
        """
        state = self._get_state(session_id)
        state.evaluation.transcript = self._build_transcript(state)

        last_values: Any = None
        for mode, chunk in self.evaluation_graph.stream(
            state, stream_mode=["updates", "values"]
        ):
            if mode == "updates":
                for node_name in chunk:
                    yield {
                        "type": "progress",
                        "node": node_name,
                        "label": _NODE_LABELS.get(node_name, node_name),
                    }
            elif mode == "values":
                last_values = chunk

        if isinstance(last_values, SessionState):
            result_state = last_values
        else:
            result_state = SessionState.model_validate(last_values)

        report = self._finalize(session_id, result_state)
        yield {"type": "report", "report": report}

    def _finalize(self, session_id: str, result_state: SessionState) -> dict:
        """Persist the report, close the session row, update the learner
        profile, and drop the in-memory state. Shared by both end variants."""
        report = result_state.report.data
        user_id = result_state.user.user_id

        db = SessionLocal()
        try:
            report_id = str(uuid.uuid4())
            ReportDAO(db).create(
                {
                    "report_id": report_id,
                    "session_id": session_id,
                    "overall_score": report.get("overall_score", 0.0),
                    "report": report,
                }
            )
            SessionDAO(db).end_session(session_id, overall_score=report.get("overall_score", 0.0))
        finally:
            db.close()

        self._update_profile(user_id, session_id, result_state)
        self._states.pop(session_id, None)

        report["session_id"] = session_id
        return report

    def _run_conversation_turn(self, state: SessionState) -> SessionState:
        result_dict = self.conversation_graph.invoke(state)
        return SessionState.model_validate(result_dict)

    def active_session_ids(self) -> set[str]:
        """IDs of sessions currently held in memory."""
        return set(self._states)

    def _get_state(self, session_id: str) -> SessionState:
        state = self._states.get(session_id)
        if state is None:
            raise KeyError(f"No active session: {session_id}")
        return state

    def _update_profile(self, user_id: str, session_id: str, state: SessionState) -> None:
        profile = profile_service.load(user_id)
        scores = state.scores
        rec = state.evaluation.recommendation
        report = state.report.data

        profile.overall_score = report.get("overall_score", profile.overall_score)
        profile.estimated_level = _advance_level(profile.estimated_level, profile.overall_score)
        profile.learning_goal = rec.get("next_session_goal") or profile.learning_goal

        g = scores.get("grammar", {})
        profile.grammar = GrammarProfile(
            score=g.get("score", profile.grammar.score),
            common_errors=g.get("common_errors", profile.grammar.common_errors),
        )
        v = scores.get("vocabulary", {})
        profile.vocabulary = VocabularyProfile(
            score=v.get("score", profile.vocabulary.score),
            lexical_diversity=v.get("lexical_diversity", profile.vocabulary.lexical_diversity),
            strengths=v.get("strengths", profile.vocabulary.strengths),
            weaknesses=v.get("weaknesses", profile.vocabulary.weaknesses),
        )
        e = scores.get("engagement", {})
        profile.engagement = EngagementProfile(
            score=e.get("score", profile.engagement.score),
            average_words=e.get("average_words", profile.engagement.average_words),
            follow_up_questions=e.get("follow_up_questions", profile.engagement.follow_up_questions),
        )
        c = scores.get("confidence", {})
        profile.confidence = ConfidenceProfile(
            score=c.get("score", profile.confidence.score),
            hedging_frequency=c.get("hedging_frequency", profile.confidence.hedging_frequency),
            notes=c.get("notes", profile.confidence.notes),
        )
        profile.recommendation = RecommendationProfile(
            next_session_goal=rec.get("next_session_goal", ""),
            homework=rec.get("homework", ""),
            exercises=rec.get("exercises", []),
        )
        if rec.get("conversation_topics"):
            profile.recommended_topics = rec["conversation_topics"]
        profile.session_history.append(session_id)

        profile_service.save(profile)
        logger.info("Updated learner profile for %s after session %s", user_id, session_id)

    @staticmethod
    def _build_transcript(state: SessionState) -> str:
        lines = []
        for msg in state.conversation.messages:
            speaker = "Learner" if msg.get("role") == "user" else "Coach"
            lines.append(f"{speaker}: {msg.get('content', '')}")
        return "\n".join(lines)


session_service = SessionService()
