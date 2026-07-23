# Roadmap

## Current focus — Minimal Voice Bot (active)
The active app is `frontend/voice_bot.py`: a single Streamlit process that
does voice/text chat on any topic and gives feedback when the conversation
ends. Whisper + `llama3.2` (Ollama) + Piper, all in one process — no FastAPI,
no LangGraph, no database. The larger platform below is **parked** (kept in
the repo, not the default) to keep the working path small and reliable.

---


## Phase 1 — Foundation (done)
- [x] Repository scaffold
- [x] Configuration system
- [x] Database connection, ORM models & DAOs
- [x] Memory / session state
- [x] Abstract agent & graph architecture
- [x] FastAPI health endpoint
- [x] Streamlit welcome page

## Phase 2 — Core AI Pipeline (done)
- [x] Ollama LLM integration (Conversation LLM + Evaluation LLM, one Ollama-resident model, two roles)
- [x] Conversation agent implementation
- [x] Speech-to-text (Faster Whisper)
- [x] Text-to-speech (Piper)

## Phase 3 — Multi-agent Conversation Graph (done)
- [x] Greeting Agent (opening context from the learner profile)
- [x] Difficulty Planner (CEFR-level guidance injected into the Conversation Agent)
- [x] Memory Manager (persists transcript turns, advances turn_count)
- [x] Conditional routing (Greeting only runs on turn 0)

## Phase 4 — Evaluation Graph (done)
- [x] Grammar, Vocabulary, Fluency, Engagement, Confidence agents
- [x] Recommendation agent (homework / drills / next-session goal)
- [x] Report generator (weighted overall score + narrative summary)
- [x] Learner profile update after every session

## Phase 5 — Session Lifecycle & Frontend (done)
- [x] `/session/start`, `/chat`, `/voice/chat`, `/session/{id}/end` endpoints
- [x] In-memory active-session registry (SessionState is the source of truth while a session runs; SQLite is persistence)
- [x] Streamlit session lifecycle (start/end buttons, report view)

## Phase 6 — Performance & Robustness (done)
- [x] Per-agent evaluation models (light `llama3.2` scorers, `qwen3:8b` reasoning)
- [x] Parallel evaluation graph (fan-out/fan-in with a scores reducer)
- [x] Recommendation node: Python-derived goal, minimal LLM prompt, no transcript
- [x] Report node: Python-assembled structure, capped `llama3.2` narrative
- [x] Per-node timing logs
- [x] Retry + timeout on all LLM calls
- [x] Dependency-checking `/health` endpoint
- [x] Streaming evaluation progress (`/session/{id}/end/stream`)
- [x] Automated test suite (unit + integration, mock-based)

## Phase 7 — Polish (done)
- [x] Multipage app (`st.navigation`): Practice + Progress
- [x] Dashboard: session history & progress charts (`/users/{id}/history`)
- [x] Typing effect on chat replies (`st.write_stream`)
- [x] PDF report export (`reports/pdf_report.py`, download button)
- [x] CI pipeline (GitHub Actions, `requirements-test.txt`)
- [x] Non-blocking backend handlers (threadpool) so long LLM calls don't stall `/health` or the dashboard

## Phase 8 — Future
- [ ] True token streaming for conversation (LangGraph `stream_mode="messages"`)
- [ ] Dashboard filters / per-skill deep dives
- [ ] Deployment (Docker Compose for backend + frontend + Ollama)

## Future (V2+)
- [ ] Pronunciation scoring, speaking speed (WPM), pause detection
- [ ] RAG over grammar references / CEFR guidelines
- [ ] Multi-language support
- [ ] Teacher dashboard
