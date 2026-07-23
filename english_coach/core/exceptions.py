# ─── core/exceptions.py ───
"""Custom exception hierarchy for English Coach."""


class EnglishCoachError(Exception):
    """Base exception for the entire application."""


# ── LLM Errors ──
class LLMError(EnglishCoachError):
    """Raised when an LLM call fails."""


class LLMConnectionError(LLMError):
    """Raised when the LLM server is unreachable."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM call exceeds the timeout."""


# ── Speech Errors ──
class SpeechError(EnglishCoachError):
    """Base class for speech-related errors."""


class STTError(SpeechError):
    """Raised when speech-to-text fails."""


class TTSError(SpeechError):
    """Raised when text-to-speech fails."""


# ── Database Errors ──
class DatabaseError(EnglishCoachError):
    """Raised on database operation failures."""


# ── Agent / Graph Errors ──
class AgentError(EnglishCoachError):
    """Raised when an agent encounters an error."""


class GraphError(EnglishCoachError):
    """Raised when a graph execution fails."""
