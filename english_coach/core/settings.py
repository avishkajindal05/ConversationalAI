# ─── core/settings.py ───
"""Pydantic Settings for English Coach.

Reads values from environment variables / .env file.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central application settings sourced from environment."""

    log_level: str = Field(default="INFO")
    ollama_host: str = Field(default="http://localhost:11434")
    # Conversation graph: the larger model for natural dialogue.
    conversation_model: str = Field(default="qwen3:8b-instruct-q4")
    # Evaluation graph, mechanical scoring (grammar/vocabulary/fluency/
    # engagement/confidence): a lighter, faster model.
    scoring_model: str = Field(default="llama3.2")
    # Evaluation graph, reasoning-heavy steps (recommendation/report): the
    # larger model, for richer language generation.
    reasoning_model: str = Field(default="qwen3:8b-instruct-q4")
    # Minimal single-process voice bot (frontend/voice_bot.py): a small, fast
    # model so voice turns stay responsive on CPU.
    voice_model: str = Field(default="llama3.2")
    whisper_model: str = Field(default="small")
    piper_model: str = Field(default="en_US-lessac-medium")
    database_path: str = Field(default="data/english_coach.db")
    api_base_url: str = Field(default="http://localhost:8000")
    audio_input_dir: str = Field(default="data/audio/input")
    audio_output_dir: str = Field(default="data/audio/output")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
