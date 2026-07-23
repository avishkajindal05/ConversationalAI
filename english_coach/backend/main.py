# ─── backend/main.py ───
"""FastAPI application entry point.

Start with:
    uvicorn english_coach.backend.main:app --reload
"""

import json
import os
import shutil
import time
import uuid

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from english_coach.core.constants import APP_NAME, APP_VERSION
from english_coach.core.logger import logger
from english_coach.core.settings import settings
from english_coach.database.models import init_db
from english_coach.services.dashboard_service import get_user_history
from english_coach.services.health_service import run_health_checks
from english_coach.services.session_service import session_service
from english_coach.speech.speech_to_text import SpeechToTextService
from english_coach.speech.text_to_speech import TextToSpeechService

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Offline AI English Speaking Coach API",
)

# Mount static files for audio output
os.makedirs(settings.audio_output_dir, exist_ok=True)
os.makedirs(settings.audio_input_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=settings.audio_output_dir), name="audio")

init_db()
stt_service = SpeechToTextService()
tts_service = TextToSpeechService()


class SessionStartRequest(BaseModel):
    user_id: str


class SessionStartResponse(BaseModel):
    session_id: str
    message: str
    difficulty: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    message: str


class VoiceChatResponse(BaseModel):
    transcript: str
    response: str
    audio_file: str


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("%s v%s starting up", APP_NAME, APP_VERSION)


# These handlers do blocking work (LLM calls, DB, dependency probes). Declaring
# them as sync `def` makes FastAPI run each in its threadpool, so a long LLM
# call on one request no longer stalls the event loop for /health, the
# dashboard, or other users.
@app.get("/health", tags=["system"])
def health_check() -> JSONResponse:
    """Liveness + dependency health (Ollama, SQLite, Whisper, Piper)."""
    result = run_health_checks()
    result["app"] = APP_NAME
    result["version"] = APP_VERSION
    # 200 when healthy/degraded (text chat still works when only speech is
    # down); 503 when a critical dependency is unavailable.
    code = 503 if result["status"] == "unhealthy" else 200
    return JSONResponse(status_code=code, content=result)


@app.post("/session/start", tags=["session"], response_model=SessionStartResponse)
def start_session(request: SessionStartRequest) -> SessionStartResponse:
    """Start a new coaching session: loads the learner profile and runs the opening turn."""
    result = session_service.start_session(request.user_id)
    return SessionStartResponse(**result)


@app.post("/session/{session_id}/end", tags=["session"])
def end_session(session_id: str) -> dict:
    """End a session, run the evaluation graph, and return the final report."""
    try:
        return session_service.end_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found or already ended.")


@app.post("/session/{session_id}/end/stream", tags=["session"])
async def end_session_stream(session_id: str) -> StreamingResponse:
    """End a session, streaming per-node progress then the final report.

    Emits newline-delimited JSON (one event per line): progress events as
    each evaluation agent finishes, then a final {"type": "report", ...}.
    """
    if session_id not in session_service.active_session_ids():
        raise HTTPException(status_code=404, detail="Session not found or already ended.")

    def _generate():
        try:
            for event in session_service.end_session_stream(session_id):
                yield json.dumps(event) + "\n"
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Streaming evaluation failed.")
            yield json.dumps({"type": "error", "detail": str(e)}) + "\n"

    return StreamingResponse(_generate(), media_type="application/x-ndjson")


@app.get("/users/{user_id}/history", tags=["dashboard"])
def user_history(user_id: str) -> dict:
    """Return the learner's evaluated session history for the dashboard."""
    return {"user_id": user_id, "history": get_user_history(user_id)}


@app.post("/chat", tags=["conversation"], response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Process one text turn within an active session."""
    try:
        reply = session_service.send_message(request.session_id, request.message)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found. Start a new session first.")
    return ChatResponse(message=reply)


def cleanup_old_audio(directory: str, max_age_seconds: int = 300) -> None:
    """Delete files in a directory older than max_age_seconds."""
    if not os.path.exists(directory):
        return
    now = time.time()
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath) and now - os.path.getmtime(filepath) > max_age_seconds:
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error("Failed to delete %s: %s", filepath, e)


@app.post("/voice/chat", tags=["conversation"], response_model=VoiceChatResponse)
def voice_chat(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> VoiceChatResponse:
    """Process one voice turn within an active session.

    Sync `def` so STT + LLM + TTS run in the threadpool (see health_check
    note). audio.file is read synchronously via shutil, so no await needed.
    """
    cleanup_old_audio(settings.audio_output_dir)

    file_id = str(uuid.uuid4())
    input_path = os.path.join(settings.audio_input_dir, f"input_{file_id}.wav")

    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)

        transcript = stt_service.transcribe(input_path)

        try:
            reply = session_service.send_message(session_id, transcript)
        except KeyError:
            raise HTTPException(status_code=404, detail="Session not found. Start a new session first.")

        output_filename = f"response_{file_id}.wav"
        output_path = os.path.join(settings.audio_output_dir, output_filename)
        tts_service.synthesize(reply, output_path)

        return VoiceChatResponse(
            transcript=transcript,
            response=reply,
            audio_file=f"/audio/{output_filename}",
        )
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
