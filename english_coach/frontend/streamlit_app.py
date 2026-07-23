# ─── frontend/streamlit_app.py ───
"""Multipage Streamlit entrypoint.

Run with:
    streamlit run english_coach/frontend/streamlit_app.py
"""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st  # noqa: E402

st.set_page_config(
    page_title="English Coach",
    page_icon=":material/school:",
    layout="centered",
)

practice = st.Page("app_pages/practice.py", title="Practice", icon=":material/forum:")
progress = st.Page("app_pages/progress.py", title="Progress", icon=":material/insights:")

nav = st.navigation([practice, progress])
nav.run()
