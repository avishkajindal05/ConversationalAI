# ─── frontend/shared.py ───
"""Shared state, backend calls, and rendering helpers for the Streamlit pages.

Not a page itself (no Streamlit page body) - just importable helpers.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import requests
import streamlit as st

# Add project root to sys.path so pages can import english_coach.
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from english_coach.core.settings import settings  # noqa: E402
from english_coach.reports.pdf_report import build_report_pdf  # noqa: E402

API = settings.api_base_url


def init_state() -> None:
    st.session_state.setdefault("user_id", "demo_user")
    st.session_state.setdefault("session_id", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("difficulty", "")
    st.session_state.setdefault("pending", None)
    st.session_state.setdefault("audio_nonce", 0)


def type_out(text: str, delay: float = 0.02) -> Iterator[str]:
    """Yield a reply word-by-word for a st.write_stream typing effect."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


def start_session() -> None:
    with st.spinner("Starting session..."):
        try:
            response = requests.post(
                f"{API}/session/start",
                json={"user_id": st.session_state.user_id},
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            st.error(f"Could not start session: {e}")
            return

    st.session_state.session_id = data["session_id"]
    st.session_state.difficulty = data.get("difficulty", "")
    st.session_state.messages = [{"role": "assistant", "content": data["message"]}]
    st.session_state.report = None


def end_session() -> None:
    session_id = st.session_state.session_id
    if not session_id:
        return

    report = None
    with st.status("Evaluating your session...", expanded=True) as status:
        try:
            with requests.post(
                f"{API}/session/{session_id}/end/stream", stream=True, timeout=1800
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("type") == "progress":
                        status.write(f":material/check_circle: {event['label']}")
                    elif event.get("type") == "report":
                        report = event["report"]
                    elif event.get("type") == "error":
                        raise RuntimeError(event.get("detail", "evaluation error"))
            status.update(label="Evaluation complete", state="complete")
        except Exception as e:
            status.update(label="Evaluation failed", state="error")
            st.error(f"Could not end session: {e}")
            return

    st.session_state.report = report
    st.session_state.session_id = None


def send_text(prompt: str) -> str:
    try:
        response = requests.post(
            f"{API}/chat",
            json={"session_id": st.session_state.session_id, "message": prompt},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]
    except Exception as e:
        return f"Error communicating with backend: {e}"


def send_voice(uploaded_file) -> dict | None:
    try:
        files = {"audio": (uploaded_file.name, uploaded_file, uploaded_file.type)}
        data = {"session_id": st.session_state.session_id}
        response = requests.post(f"{API}/voice/chat", files=files, data=data, timeout=180)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error communicating with backend: {e}")
        return None


def render_report(report: dict) -> None:
    st.subheader("Session report")
    st.metric("Overall score", f"{report.get('overall_score', 0):.0f} / 100")
    st.write(report.get("summary", ""))

    with st.container(horizontal=True):
        with st.container(border=True):
            st.markdown("**Strengths**")
            for item in report.get("strengths", []):
                st.markdown(f"- {item}")
        with st.container(border=True):
            st.markdown("**Weaknesses**")
            for item in report.get("weaknesses", []):
                st.markdown(f"- {item}")

    if report.get("progress"):
        st.info(report["progress"])

    recommendation = report.get("recommendation", {})
    if recommendation:
        with st.container(border=True):
            st.markdown("**Next steps**")
            st.markdown(f"*Goal:* {recommendation.get('next_session_goal', '')}")
            st.markdown(f"*Homework:* {recommendation.get('homework', '')}")
            for exercise in recommendation.get("exercises", []):
                st.markdown(f"- {exercise}")

    st.download_button(
        "Download PDF report",
        data=build_report_pdf(report),
        file_name=f"english_coach_report_{report.get('session_id', 'session')}.pdf",
        mime="application/pdf",
        icon=":material/download:",
    )

    with st.expander("Detailed scores"):
        st.json(report.get("scores", {}))
