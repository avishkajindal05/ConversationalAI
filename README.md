# ConversationalAI - Voice Bot

A small, offline **voice bot**: have a spoken (or typed) conversation on any
everyday topic, then end the conversation to get friendly feedback on your
spoken English and communication. Everything runs locally with open-source
models.

## Quick start (the voice bot)

This is the primary app — **one Streamlit process**, no backend, no database.

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

Open the URL it prints (default http://localhost:8501). Talk (record a voice
message) or type, chat about anything, then click **End conversation & get
feedback** in the sidebar.

### How it works
```
microphone --> Faster-Whisper (STT) --> Ollama LLM (llama3.2) --> Piper (TTS) --> speaker
                                              |
                        (on "End") analyse the transcript --> feedback
```
All models are open-source and run offline: **Faster-Whisper** (speech-to-text),
**llama3.2** via **Ollama** (chat + feedback), **Piper** (text-to-speech). On
first run, Whisper and Piper download their model files once.

> On CPU, a voice turn takes roughly 15-20s end to end (transcribe + generate +
> speak). That's expected for local inference.

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
