# ConversationalAI - Communication Coach

A small, offline **communication coach**. Have a spoken or typed conversation
(or upload a transcript / audio file); when you end it, the bot scores your
communication, tracks whether previously flagged issues **improved / stayed
the same / got worse** across sessions, and charts your progress. Everything
runs locally on open-source models.

## Quick start

The primary app is **one Streamlit process** — Whisper + `llama3.2` (Ollama) +
Piper, plus a tiny SQLite file for progress. No backend server, no LangGraph.

**1. Install**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**2. Start Ollama with the model pulled** (open-source, runs locally)
```bash
ollama pull llama3.2
ollama serve
```

**3. Run the bot**
```bash
streamlit run english_coach/frontend/voice_bot.py
```

Open the URL it prints (default http://localhost:8501). Enter a **Candidate
ID**, pick an input method, have the conversation (or upload), then
**End conversation & analyse**. Switch the sidebar **View** to **Progress** to
see score trends and the issue tracker across sessions with the same ID.

### How it works
```
live text / live voice / upload transcript / upload audio
        |                                    |
        v                                    v
  Faster-Whisper (STT) --> llama3.2 (Ollama, streamed) --> Piper (TTS)
        |
        v  (on "Analyse")
  transcript + issues still open from the last session
        |
        v
  one structured, Pydantic-validated llama3.2 call:
    scores + per-issue verdicts (improved/unchanged/worse) + new issues + summary
        |
        v
  saved to SQLite  -->  Progress view: score trends + issue tracker
```

**Design notes**
- **Streamed replies** — the bot's reply appears token-by-token as it's
  generated, so on CPU you start reading a few seconds in instead of waiting
  for the whole reply. The full text is still captured for scoring.
- **Structured, validated analysis** — the scoring call returns JSON validated
  against a Pydantic schema (`coach/schema.py`) and retries on invalid output,
  because a 3B model isn't perfectly reliable at strict JSON.
- **Cross-session tracking** — a single SQLite table (`data/coach.db`) carries
  open issues forward so the next session can judge whether each improved.
- **Cascaded voice, on purpose** — turn-based Whisper→LLM→Piper stays
  controllable and hands you a clean transcript to score. Native
  speech-to-speech (e.g. Moshi) is lower-latency but can't be steered or scored
  the same way, and doesn't fit CPU-only hardware.

> On CPU a turn is roughly 15-20s end to end (transcribe + generate + speak),
> and the analysis is ~10s. That's expected for local inference; keeping the
> model warm (Ollama `keep_alive`) avoids reload cost between turns.

---

## Full agentic platform (parked / experimental)

The repository also contains a larger "English Coach" platform — a FastAPI
backend, two LangGraph graphs (a multi-agent conversation graph and a 7-agent
evaluation graph), SQLite persistence, learner profiles, and a multipage
dashboard. It works but has more moving parts (two processes, heavier models),
so it is **not the default**. See [docs/architecture.md](english_coach/docs/architecture.md)
and [docs/development-log.md](english_coach/docs/development-log.md) for the
full design and history.

To run the full platform instead of the voice bot:
```bash
ollama pull qwen3:8b && ollama pull llama3.2 && ollama serve
uvicorn english_coach.backend.main:app            # terminal 1
streamlit run english_coach/frontend/streamlit_app.py   # terminal 2
```
