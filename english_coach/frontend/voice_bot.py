# ─── frontend/voice_bot.py ───
"""Minimal single-process voice bot.

Have a spoken (or typed) conversation on any topic; when you end it, the bot
analyses the chat and gives you feedback. Everything runs in this one
Streamlit process using open-source models:

    microphone --> Faster-Whisper (STT) --> Ollama LLM (llama3.2) --> Piper (TTS)

No FastAPI, no LangGraph, no database. Run with:
    streamlit run english_coach/frontend/voice_bot.py
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage  # noqa: E402
from langchain_ollama import ChatOllama  # noqa: E402

from english_coach.core.settings import settings  # noqa: E402
from english_coach.speech.speech_to_text import SpeechToTextService  # noqa: E402
from english_coach.speech.text_to_speech import TextToSpeechService  # noqa: E402

CHAT_SYSTEM = (
    "You are a warm, curious voice conversation partner. You can chat about "
    "any everyday topic - hobbies, travel, food, films, work, plans, ideas. "
    "Keep every reply short and natural, like spoken language (1-3 sentences). "
    "Always finish with a friendly question so the conversation keeps flowing. "
    "Never lecture, never use bullet lists."
)

FEEDBACK_SYSTEM = (
    "You are a kind communication coach. You are given a transcript of a "
    "spoken conversation. Look only at the USER's messages and give brief, "
    "encouraging feedback on their spoken English and communication. "
    "Reply in short markdown with exactly these sections:\n"
    "**Overall** - one or two encouraging sentences.\n"
    "**What went well** - 2-3 short points.\n"
    "**Suggestions** - 2-3 concrete, kind tips.\n"
    "Keep it under 180 words. Do not invent details that are not in the transcript."
)

OPENING = (
    "Hey, great to meet you! I'm happy to chat about pretty much anything - "
    "hobbies, travel, food, films, whatever's on your mind. "
    "So, what have you been up to lately?"
)


# ── Cached heavy resources (load once per Streamlit server) ──────────────────
@st.cache_resource(show_spinner="Loading language model...")
def get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.voice_model,
        base_url=settings.ollama_host,
        num_predict=200,  # short, spoken-length replies
    )


@st.cache_resource(show_spinner="Loading speech recogniser...")
def get_stt() -> SpeechToTextService:
    service = SpeechToTextService()
    service.load_model()
    return service


@st.cache_resource(show_spinner="Loading voice...")
def get_tts() -> TextToSpeechService:
    service = TextToSpeechService()
    service.load_model()
    return service


# ── Core helpers ─────────────────────────────────────────────────────────────
def generate_reply(messages: list[dict]) -> str:
    lc = [SystemMessage(content=CHAT_SYSTEM)]
    for m in messages:
        if m["role"] == "user":
            lc.append(HumanMessage(content=m["content"]))
        else:
            lc.append(AIMessage(content=m["content"]))
    try:
        return get_llm().invoke(lc).content.strip()
    except Exception as e:
        return f"Sorry, I had trouble responding ({e}). Could you try again?"


def synthesize(text: str) -> bytes | None:
    """Turn text into spoken audio bytes, or None if TTS fails."""
    try:
        tts = get_tts()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name
        tts.synthesize(text, out_path)
        data = Path(out_path).read_bytes()
        Path(out_path).unlink(missing_ok=True)
        return data
    except Exception:
        return None  # voice is optional; text reply still shows


def transcribe(audio_file) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_file.getvalue())
        path = tmp.name
    try:
        return get_stt().transcribe(path)
    finally:
        Path(path).unlink(missing_ok=True)


def generate_feedback(messages: list[dict]) -> str:
    transcript = "\n".join(
        f"{'User' if m['role'] == 'user' else 'Bot'}: {m['content']}" for m in messages
    )
    try:
        return get_llm().invoke(
            [SystemMessage(content=FEEDBACK_SYSTEM), HumanMessage(content=transcript)]
        ).content.strip()
    except Exception as e:
        return f"Could not generate feedback ({e})."


def add_turn(user_text: str) -> None:
    """Append a user message, get + speak the bot's reply."""
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.spinner("Thinking..."):
        reply = generate_reply(st.session_state.messages)
        audio = synthesize(reply)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "audio": audio}
    )


# ── State ────────────────────────────────────────────────────────────────────
def init_state() -> None:
    if "messages" not in st.session_state:
        opening_audio = synthesize(OPENING)
        st.session_state.messages = [
            {"role": "assistant", "content": OPENING, "audio": opening_audio}
        ]
    st.session_state.setdefault("feedback", None)
    st.session_state.setdefault("mic_nonce", 0)


def reset() -> None:
    for key in ("messages", "feedback", "mic_nonce"):
        st.session_state.pop(key, None)


# ── Page ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Voice Bot",
    page_icon=":material/graphic_eq:",
    layout="centered",
    initial_sidebar_state="expanded",
)
init_state()

st.title("Voice Bot")
st.caption("Have a chat about anything. When you're done, end the conversation for feedback.")

@st.dialog("Your feedback", width="large")
def feedback_dialog() -> None:
    """Show feedback in a centred modal so it can't be missed.

    The old inline version rendered at the top of the page; a user scrolled
    down at the mic saw neither the spinner nor the result. Generating inside
    the dialog keeps the "analysing…" state on-screen the whole time.
    """
    user_turns = [m for m in st.session_state.messages if m["role"] == "user"]
    if not user_turns:
        st.warning("Say something first, then end the conversation for feedback.")
        return
    if st.session_state.get("feedback") is None:
        with st.spinner("Analysing your conversation… (this can take up to a minute on CPU)"):
            st.session_state.feedback = generate_feedback(st.session_state.messages)
    st.markdown(st.session_state.feedback)


with st.sidebar:
    st.markdown("**Conversation**")
    st.caption(f"Model: `{settings.voice_model}` (offline via Ollama)")
    end_clicked = st.button(
        "End conversation & get feedback", width="stretch", type="primary"
    )
    if st.button("Start over", width="stretch"):
        reset()
        st.rerun()

# Open the feedback modal when the user ends the conversation.
if end_clicked:
    st.session_state.feedback = None  # force a fresh analysis each time
    feedback_dialog()

# Keep the feedback on the page too, so it can be re-read after the modal closes.
if st.session_state.feedback:
    with st.container(border=True):
        st.subheader("Your feedback")
        st.markdown(st.session_state.feedback)
    st.divider()

# Conversation history.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/wav", autoplay=False)

# Input: voice by default, text as a reliable fallback.
mode = st.segmented_control("Input", ["Voice", "Text"], default="Voice")

if mode == "Text":
    if prompt := st.chat_input("Type a message..."):
        add_turn(prompt)
        st.rerun()
else:
    audio_value = st.audio_input("Record a message", key=f"mic_{st.session_state.mic_nonce}")
    if audio_value:
        with st.spinner("Listening..."):
            text = transcribe(audio_value)
        if text.strip():
            add_turn(text)
        else:
            st.warning("I couldn't hear anything - try recording again.")
        st.session_state.mic_nonce += 1  # reset the recorder for the next turn
        st.rerun()
