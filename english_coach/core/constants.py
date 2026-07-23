# ─── core/constants.py ───
"""Application-wide constants."""

APP_NAME = "English Coach"
APP_VERSION = "0.1.0"

# Default timeouts (seconds). Generous because an 8B model on CPU can take
# 90s+ for a single conversation turn.
DEFAULT_LLM_TIMEOUT = 300
DEFAULT_STT_TIMEOUT = 30
DEFAULT_TTS_TIMEOUT = 30

# Retry attempts for LLM calls before giving up / falling back.
LLM_RETRY_ATTEMPTS = 2

# Cap generated tokens for the short narrative summary (Report agent).
REPORT_SUMMARY_MAX_TOKENS = 400

# Database
DB_ECHO = False

# Audio
SAMPLE_RATE = 16000
AUDIO_FORMAT = "wav"
