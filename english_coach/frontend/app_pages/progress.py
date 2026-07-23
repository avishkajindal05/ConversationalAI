# ─── frontend/app_pages/progress.py ───
"""Progress page: session history and score trends."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd  # noqa: E402
import requests  # noqa: E402
import streamlit as st  # noqa: E402

from english_coach.frontend import shared  # noqa: E402

shared.init_state()

st.title("Progress")
st.caption("Your scores across past sessions")

user_id = st.session_state.get("user_id", "demo_user")
st.text_input("Learner ID", key="user_id")

try:
    resp = requests.get(f"{shared.API}/users/{user_id}/history", timeout=30)
    resp.raise_for_status()
    history = resp.json().get("history", [])
except Exception as e:
    st.error(f"Could not load history: {e}")
    st.stop()

if not history:
    st.info("No completed sessions yet. Finish a practice session to see progress here.")
    st.stop()

df = pd.DataFrame(history)
df.insert(0, "session", [f"S{i + 1}" for i in range(len(df))])

skill_cols = [
    c for c in ["grammar", "vocabulary", "fluency", "engagement", "confidence"] if c in df
]

# Headline metrics
latest, first = history[-1], history[0]
delta = (
    round(latest["overall_score"] - first["overall_score"], 1) if len(history) > 1 else None
)
with st.container(horizontal=True):
    st.metric("Sessions completed", len(history))
    st.metric("Latest overall", f"{latest['overall_score']:.0f}", delta=delta)
    st.metric("Best overall", f"{max(h['overall_score'] for h in history):.0f}")

st.subheader("Overall score trend")
st.line_chart(df, x="session", y="overall_score", height=260)

if skill_cols:
    st.subheader("Per-skill trend")
    st.line_chart(df, x="session", y=skill_cols, height=300)

st.subheader("Session history")
st.dataframe(
    df[["session", "date", "overall_score", *skill_cols]],
    hide_index=True,
    width="stretch",
)
