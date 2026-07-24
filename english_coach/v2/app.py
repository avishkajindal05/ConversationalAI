# ─── v2/app.py ───
"""Communication coach - single-process voice bot.

Have a spoken or typed conversation (or upload a transcript / audio file);
when you end it, the bot scores your communication, tracks whether previously
flagged issues improved, and shows your progress across sessions. Everything
runs locally on open-source models:

    microphone --> Faster-Whisper (STT) --> llama3.2 (Ollama) --> Piper (TTS)
                              |
              (on analyse) transcript + prior issues --> structured report

Run with:
    streamlit run english_coach/v2/app.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from langchain_ollama import ChatOllama  # noqa: E402

from english_coach.v2.coach import db  # noqa: E402
from english_coach.v2.coach.analysis import analyze  # noqa: E402
from english_coach.v2.coach.conversation import OPENING, stream_reply, transcript_text  # noqa: E402
from english_coach.v2.coach.schema import METRICS  # noqa: E402
from english_coach.core.settings import settings  # noqa: E402
from english_coach.speech.speech_to_text import SpeechToTextService  # noqa: E402
from english_coach.speech.text_to_speech import TextToSpeechService  # noqa: E402

_STATUS = {
    "improved": ("🟢", "Improved"),
    "unchanged": ("🟡", "Unchanged"),
    "worse": ("🔴", "Worse"),
}


# ── Cached heavy resources (load once per Streamlit server) ──────────────────
@st.cache_resource(show_spinner="Loading language model...")
def get_chat_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.voice_model,
        base_url=settings.ollama_host,
        num_predict=200,  # short, spoken-length replies
        keep_alive="30m",  # keep the model resident so later turns skip reload
        client_kwargs={"timeout": 300},  # fail out instead of hanging if Ollama stalls
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


# ── Helpers ──────────────────────────────────────────────────────────────────
def synthesize(text: str) -> bytes | None:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name
        get_tts().synthesize(text, out_path)
        data = Path(out_path).read_bytes()
        Path(out_path).unlink(missing_ok=True)
        return data
    except Exception:
        return None  # voice is optional; text still shows


def transcribe(audio_file) -> str:
    suffix = Path(getattr(audio_file, "name", "clip.wav")).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_file.getvalue())
        path = tmp.name
    try:
        return get_stt().transcribe(path)
    finally:
        Path(path).unlink(missing_ok=True)


def handle_turn(user_text: str) -> None:
    """Append the user turn and stream the reply (speaking only if enabled)."""
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)
    with st.chat_message("assistant"):
        with st.spinner("Thinking… (the first reply after startup can take ~15s on CPU)"):
            full = st.write_stream(stream_reply(get_chat_llm(), st.session_state.messages))
    audio = synthesize(full) if st.session_state.get("speak") else None
    st.session_state.messages.append({"role": "assistant", "content": full, "audio": audio})


def run_analysis(candidate_id: str, transcript: str, source: str) -> None:
    with st.status("Analysing your communication…", expanded=True) as status:
        prior = db.latest_open_issues(candidate_id)
        if prior:
            status.write(f"Comparing against {len(prior)} issue(s) from last session…")
        result = analyze(transcript, prior)
        open_issues = result.open_issues(prior)
        db.save_session(candidate_id, source, transcript, result, open_issues)
        st.session_state.report = {**result.model_dump(), "overall_score": result.overall_score}
        st.session_state.last_transcript = transcript
        status.update(label="Analysis complete", state="complete")


# ── State ────────────────────────────────────────────────────────────────────
def init_state() -> None:
    st.session_state.setdefault("candidate_id", "demo")
    if "messages" not in st.session_state:
        # No audio on the opening — the bot only speaks if the user opts in,
        # and nothing is synthesised (or auto-played) on startup.
        st.session_state.messages = [{"role": "assistant", "content": OPENING}]
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("mic_nonce", 0)
    st.session_state.setdefault("upload_text", "")
    st.session_state.setdefault("speak", False)
    st.session_state.setdefault("last_transcript", "")


def reset_conversation() -> None:
    for key in ("messages", "report", "mic_nonce", "upload_text"):
        st.session_state.pop(key, None)


# ── Report + progress rendering ──────────────────────────────────────────────
def render_report(report: dict) -> None:
    with st.container(border=True):
        st.subheader("Your report")
        cols = st.columns(len(METRICS) + 1)
        cols[0].metric("Overall", f"{report.get('overall_score', 0):.0f}")
        for col, metric in zip(cols[1:], METRICS):
            col.metric(metric.capitalize(), report.get("scores", {}).get(metric, 0))

        if report.get("summary"):
            st.write(report["summary"])

        if report.get("strengths"):
            st.markdown("**✅ What went well**")
            for s in report["strengths"]:
                st.markdown(f"- {s}")

        verdicts = report.get("prior_issue_verdicts", [])
        if verdicts:
            st.markdown("**📈 What changed since last session**")
            for v in verdicts:
                icon, label = _STATUS.get(v.get("status", "unchanged"), ("🟡", "Unchanged"))
                st.markdown(f"{icon} **{label}** — {v.get('description', '')}")
                if v.get("evidence"):
                    st.caption(v["evidence"])

        new_issues = report.get("new_issues", [])
        if new_issues:
            st.markdown("**⚠️ What to work on**")
            for it in new_issues:
                st.markdown(
                    f"- {it.get('description', '')} "
                    f"*({it.get('category', 'general')}, {it.get('severity', 'medium')})*"
                )

        if st.session_state.get("last_transcript"):
            st.download_button(
                "Download transcript",
                data=st.session_state.last_transcript,
                file_name=f"{st.session_state.candidate_id}_transcript.txt",
                mime="text/plain",
                icon=":material/download:",
            )


def _issue_tracker(sessions: list[dict]) -> pd.DataFrame:
    agg: dict[str, dict] = {}
    for s in sessions:
        for it in s["new_issues"]:
            desc = it["description"]
            row = agg.setdefault(
                desc,
                {
                    "issue": desc,
                    "category": it.get("category", "general"),
                    "severity": it.get("severity", "medium"),
                    "sessions_flagged": 0,
                    "latest_status": "open",
                },
            )
            row["sessions_flagged"] += 1
        for v in s["verdicts"]:
            if v["description"] in agg:
                agg[v["description"]]["latest_status"] = v["status"]
    return pd.DataFrame(list(agg.values()))


def render_progress(candidate_id: str) -> None:
    st.title("Progress")
    st.caption(f"Communication trends for `{candidate_id}`")
    sessions = db.all_sessions(candidate_id)
    if not sessions:
        st.info("No analysed sessions yet. Have a conversation and analyse it first.")
        return

    rows = []
    for i, s in enumerate(sessions, 1):
        row = {"session": f"S{i}", "overall": s["overall_score"]}
        row.update(s["scores"])
        rows.append(row)
    df = pd.DataFrame(rows)

    first, latest = sessions[0], sessions[-1]
    delta = round(latest["overall_score"] - first["overall_score"], 1) if len(sessions) > 1 else None
    c1, c2, c3 = st.columns(3)
    c1.metric("Sessions", len(sessions))
    c2.metric("Latest overall", f"{latest['overall_score']:.0f}", delta=delta)
    c3.metric("Best overall", f"{max(s['overall_score'] for s in sessions):.0f}")

    st.subheader("Score trend")
    st.line_chart(df, x="session", y=["overall", *METRICS], height=300)

    st.subheader("Issue tracker")
    tracker = _issue_tracker(sessions)
    if tracker.empty:
        st.caption("No issues flagged yet.")
    else:
        st.dataframe(tracker, hide_index=True, width="stretch")


# ── Practice view ────────────────────────────────────────────────────────────
def render_practice(candidate_id: str) -> None:
    st.title("Communication coach")
    st.caption("Chat, upload a transcript, or upload audio — then analyse it.")

    if st.session_state.report:
        render_report(st.session_state.report)
        st.divider()

    method = st.segmented_control(
        "Input",
        ["Live text", "Live voice", "Upload transcript", "Upload audio"],
        default="Live text",
    )

    if method in ("Live text", "Live voice"):
        _render_live(candidate_id, method)
    else:
        _render_upload(candidate_id, method)


def _render_live(candidate_id: str, method: str) -> None:
    st.toggle(
        "🔊 Speak the bot's replies",
        key="speak",
        help="Off by default. When on, each reply is voiced so you can play it — it never auto-plays.",
    )

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/wav", autoplay=False)

    has_user_turn = any(m["role"] == "user" for m in st.session_state.messages)
    if has_user_turn:
        end_col, dl_col = st.columns(2)
        if end_col.button("End conversation & analyse", type="primary", width="stretch"):
            run_analysis(candidate_id, transcript_text(st.session_state.messages), "live")
            st.rerun()
        dl_col.download_button(
            "Download transcript",
            data=transcript_text(st.session_state.messages),
            file_name=f"{candidate_id}_transcript.txt",
            mime="text/plain",
            width="stretch",
        )

    if method == "Live text":
        if prompt := st.chat_input("Type a message..."):
            handle_turn(prompt)
            st.rerun()
    else:
        clip = st.audio_input("Record a message", key=f"mic_{st.session_state.mic_nonce}")
        if clip:
            with st.spinner("Listening..."):
                text = transcribe(clip)
            if text.strip():
                handle_turn(text)
            else:
                st.warning("I couldn't hear anything — try again.")
            st.session_state.mic_nonce += 1
            st.rerun()


def _render_upload(candidate_id: str, method: str) -> None:
    if method == "Upload transcript":
        uploaded = st.file_uploader("Transcript (.txt)", type=["txt"])
        if uploaded is not None:
            st.session_state.upload_text = uploaded.getvalue().decode("utf-8", "replace")
        source = "upload_transcript"
    else:
        uploaded = st.file_uploader("Audio file", type=["wav", "mp3", "m4a", "ogg"])
        if uploaded is not None and st.button("Transcribe"):
            with st.spinner("Transcribing…"):
                st.session_state.upload_text = transcribe(uploaded)
        source = "upload_audio"

    if st.session_state.upload_text:
        st.text_area("Transcript to analyse", st.session_state.upload_text, height=200, disabled=True)
        if st.button("Analyse", type="primary", width="stretch"):
            run_analysis(candidate_id, st.session_state.upload_text, source)
            st.rerun()


# ── Page ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Communication Coach",
    page_icon=":material/graphic_eq:",
    layout="centered",
    initial_sidebar_state="collapsed",
)
init_state()

# Top controls live in the main area (not the sidebar) so they can't vanish if
# Streamlit collapses the sidebar off-screen.
id_col, reset_col = st.columns([3, 1], vertical_alignment="bottom")
with id_col:
    st.text_input("Candidate ID", key="candidate_id")
with reset_col:
    if st.button("Start over", width="stretch"):
        reset_conversation()
        st.rerun()

view = st.segmented_control("View", ["Practice", "Progress"], default="Practice") or "Practice"
st.caption(f"Model: `{settings.voice_model}` (offline via Ollama)")

if view == "Progress":
    render_progress(st.session_state.candidate_id)
else:
    render_practice(st.session_state.candidate_id)
