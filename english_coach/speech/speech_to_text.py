# ─── speech/speech_to_text.py ───
"""Speech-to-text service using Faster Whisper."""

from __future__ import annotations

from faster_whisper import WhisperModel

from english_coach.core.settings import settings
from english_coach.core.logger import logger


class SpeechToTextService:
    """Service wrapping Faster Whisper for offline speech recognition."""

    def __init__(self) -> None:
        self.model_name = settings.whisper_model
        self._model = None
        logger.info("SpeechToTextService -> model=%s", self.model_name)

    def load_model(self) -> None:
        """Load the Whisper model."""
        if self._model is not None:
            return
            
        logger.info("Loading Whisper model: %s", self.model_name)
        # Using CPU and int8 for compatibility, can be configured later for GPU
        self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded successfully.")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text."""
        if self._model is None:
            self.load_model()
            
        logger.info("Transcribing audio file: %s", audio_path)
        segments, info = self._model.transcribe(audio_path, beam_size=5)
        
        text = " ".join([segment.text for segment in segments]).strip()
        logger.debug("Transcription complete: %s", text)
        return text
