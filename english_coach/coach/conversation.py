# ─── coach/conversation.py ───
"""Live conversation prompts and streaming reply helper.

Streaming lets the reply appear token-by-token as the model generates it, so
on CPU the user starts reading a few seconds in instead of waiting for the
whole reply. The caller accumulates the streamed chunks, so the full text is
still available for the transcript.
"""

from __future__ import annotations

from collections.abc import Iterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

CHAT_SYSTEM = (
    "You are a warm, curious conversation partner helping someone practise "
    "their spoken communication. Chat about any everyday topic - hobbies, "
    "travel, food, films, work, plans, opinions. Keep every reply short and "
    "natural, like speech (1-3 sentences). Always finish with a friendly "
    "question so the conversation keeps flowing. Never lecture, never use "
    "bullet lists."
)

OPENING = (
    "Hey, great to meet you! I'm happy to chat about pretty much anything - "
    "hobbies, travel, food, films, whatever's on your mind. "
    "So, what have you been up to lately?"
)


def to_lc_messages(messages: list[dict]) -> list:
    """Convert stored {role, content} dicts to LangChain messages."""
    lc = [SystemMessage(content=CHAT_SYSTEM)]
    for m in messages:
        if m["role"] == "user":
            lc.append(HumanMessage(content=m["content"]))
        else:
            lc.append(AIMessage(content=m["content"]))
    return lc


def stream_reply(llm, messages: list[dict]) -> Iterator[str]:
    """Yield reply chunks as the model generates them.

    `llm` is a ChatOllama instance (passed in so Streamlit can cache it).
    Falls back to a single friendly message if streaming fails.
    """
    try:
        for chunk in llm.stream(to_lc_messages(messages)):
            if chunk.content:
                yield chunk.content
    except Exception:
        yield "Sorry, I had trouble responding just now. Could you say that again?"


def transcript_text(messages: list[dict]) -> str:
    """Render the conversation as a labelled transcript for analysis."""
    return "\n".join(
        f"{'User' if m['role'] == 'user' else 'Coach'}: {m['content']}" for m in messages
    )
