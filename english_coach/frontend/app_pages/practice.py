# ─── frontend/app_pages/practice.py ───
"""Practice page: text + voice conversation with the coach."""

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st  # noqa: E402

from english_coach.frontend import shared  # noqa: E402

shared.init_state()
# Guaranteed here too: page scripts re-exec every rerun, but shared.py is a
# cached import, so a freshly added key in init_state() may not take effect
# until Streamlit is fully restarted.
st.session_state.setdefault("audio_nonce", 0)

st.title("English Coach")
st.caption("Practise your spoken English")

# Buttons only set flags; the actual work runs below so st.status/st.spinner
# output renders (callbacks cannot paint UI).
with st.sidebar:
    st.text_input("Learner ID", key="user_id", disabled=bool(st.session_state.session_id))
    if not st.session_state.session_id:
        if st.button("Start session", width="stretch"):
            st.session_state.pending = "start"
    else:
        if st.session_state.difficulty:
            st.caption(f"Difficulty: {st.session_state.difficulty}")
        if st.button("End session & get report", width="stretch"):
            st.session_state.pending = "end"

if st.session_state.get("pending") == "start":
    st.session_state.pending = None
    shared.start_session()
elif st.session_state.get("pending") == "end":
    st.session_state.pending = None
    shared.end_session()

if st.session_state.report:
    shared.render_report(st.session_state.report)
    st.divider()

if not st.session_state.session_id:
    st.info("Start a session from the sidebar to begin practising.")
    st.stop()

mode = st.segmented_control("Mode", ["Text chat", "Voice chat"], default="Text chat")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("audio_file"):
            st.audio(f"{shared.API}{message['audio_file']}")

if mode == "Text chat":
    if prompt := st.chat_input("Say something in English..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.spinner("Thinking..."):
            reply = shared.send_text(prompt)
        with st.chat_message("assistant"):
            st.write_stream(shared.type_out(reply))
        st.session_state.messages.append({"role": "assistant", "content": reply})
else:
    # Dynamic key so the widget resets to a fresh Record button after each
    # turn; otherwise it keeps showing playback of the previous clip and there
    # is no way to record again (and the old clip risks being reprocessed).
    audio_value = st.audio_input(
        "Record a voice message", key=f"voice_{st.session_state.audio_nonce}"
    )
    if audio_value:
        with st.spinner("Processing audio & thinking..."):
            result = shared.send_voice(audio_value)
        if result:
            st.session_state.messages.append({"role": "user", "content": result["transcript"]})
            with st.chat_message("user"):
                st.markdown(result["transcript"])
            with st.chat_message("assistant"):
                st.write_stream(shared.type_out(result["response"]))
                if result.get("audio_file"):
                    st.audio(f"{shared.API}{result['audio_file']}")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["response"],
                    "audio_file": result.get("audio_file"),
                }
            )
            # Reset the recorder widget and rerun so a fresh mic is shown.
            st.session_state.audio_nonce += 1
            st.rerun()
