# v2 architecture

## Overview

v2 is one Streamlit process. It has no FastAPI server, LangGraph workflow, or
ORM. The application entry point is `english_coach/v2/app.py`.

```text
Streamlit UI: Candidate ID · Practice · Progress
        |
        +--> Live text ----------------------------+
        +--> Live voice -> Faster-Whisper ---------+--> streamed Ollama llama3.2 reply
        +--> Transcript/audio upload -> transcript -+          |
                                                              optional Piper TTS
                                                                  |
                                                                  v
                  transcript + prior open issues -> one strict analysis call
                                                                  |
                                                                  v
                                      SQLite `data/coach.db` -> report and trends
```

## Components

| Component | File | Responsibility |
| --- | --- | --- |
| UI and state | `v2/app.py` | Renders practice/progress views and manages live conversation state. |
| Conversation | `v2/coach/conversation.py` | Builds prompts, streams replies, formats transcripts. |
| Analysis | `v2/coach/analysis.py` | Runs one JSON-mode Ollama call and retries invalid output. |
| Contract | `v2/coach/schema.py` | Defines strict scores, issue verdicts, and issue carry-forward rules. |
| Persistence | `v2/coach/db.py` | Stores completed analyses in SQLite with JSON columns. |
| Speech | `speech/` | Faster-Whisper transcription and optional Piper synthesis. |

## Main flows

### Conversation

1. The learner types a message or records a clip.
2. Voice clips are transcribed with Faster-Whisper on CPU using `int8`, greedy
   decoding, and voice-activity filtering.
3. The conversation helper streams a short `llama3.2` reply into Streamlit.
4. If enabled, Piper synthesizes the completed reply for manual playback.

### Analysis and progress

1. The app creates a labelled transcript.
2. It loads prior open issues for the Candidate ID.
3. One Ollama call returns scores, strengths, issue verdicts, new issues, and
   a summary.
4. Strict validation must pass before the result is saved.
5. SQLite powers score trends and the issue tracker in Progress.

## Latency decisions

- Token-streamed replies reduce perceived chat latency.
- One structured analysis call replaces v1's multi-agent evaluation calls.
- Streamlit caches the chat LLM, Whisper, and Piper resources.
- Speech output is off by default, so text interaction does not wait for TTS.

