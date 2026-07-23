# ─── llm/client.py ───
"""Low-level Ollama client wrapper."""

from __future__ import annotations

from english_coach.core.settings import settings
from english_coach.core.logger import logger


class OllamaClient:
    """Thin wrapper around the Ollama HTTP API."""

    def __init__(self, host: str | None = None) -> None:
        self.host = host or settings.ollama_host
        logger.info("OllamaClient initialised → %s", self.host)

    def generate(self, model: str, prompt: str, **kwargs) -> str:
        """Send a generate request to Ollama. Placeholder."""
        raise NotImplementedError("OllamaClient.generate() not yet implemented")

    def chat(self, model: str, messages: list[dict], **kwargs) -> str:
        """Send a chat request to Ollama. Placeholder."""
        raise NotImplementedError("OllamaClient.chat() not yet implemented")
