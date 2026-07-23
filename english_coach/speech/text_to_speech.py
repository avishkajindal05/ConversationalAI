# ─── speech/text_to_speech.py ───
"""Text-to-speech service using Piper."""

from __future__ import annotations

import os
import urllib.request
import wave
from pathlib import Path

from piper import PiperVoice

from english_coach.core.settings import settings
from english_coach.core.logger import logger


class TextToSpeechService:
    """Service wrapping Piper TTS for offline speech synthesis."""

    def __init__(self) -> None:
        self.model_name = settings.piper_model
        self._model = None
        self.model_dir = Path("data/models/piper")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.model_dir / f"{self.model_name}.onnx"
        self.config_path = self.model_dir / f"{self.model_name}.onnx.json"
        
        # Determine URLs based on model name
        # Default Piper HuggingFace structure
        base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
        self.model_url = f"{base_url}/{self.model_name}.onnx"
        self.config_url = f"{base_url}/{self.model_name}.onnx.json"

        logger.info("TextToSpeechService -> model=%s", self.model_name)

    def load_model(self) -> None:
        """Load the Piper model, downloading it if necessary."""
        if self._model is not None:
            return

        if not self.model_path.exists():
            logger.info("Downloading Piper model from %s", self.model_url)
            urllib.request.urlretrieve(self.model_url, self.model_path)
            
        if not self.config_path.exists():
            logger.info("Downloading Piper config from %s", self.config_url)
            urllib.request.urlretrieve(self.config_url, self.config_path)

        logger.info("Loading Piper model from %s", self.model_path)
        self._model = PiperVoice.load(str(self.model_path))
        logger.info("Piper model loaded successfully.")

    def synthesize(self, text: str, output_path: str) -> str:
        """Convert text to speech and save to output_path."""
        if self._model is None:
            self.load_model()
            
        logger.info("Synthesizing speech to %s", output_path)
        
        # Piper synthesizes to wave file
        with wave.open(output_path, "wb") as wav_file:
            self._model.synthesize_wav(text, wav_file)
            
        return output_path
