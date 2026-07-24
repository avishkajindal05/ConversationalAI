# Roadmap

## Current focus — Communication Coach (active)
The active app is `v2/app.py` + the `v2/coach/` package: a single
Streamlit process that does voice/text chat (or transcript/audio upload),
then runs one structured, Pydantic-validated `llama3.2` call to score
communication and track whether prior issues improved/unchanged/worse across
sessions (SQLite). Whisper + `llama3.2` (Ollama, streamed) + Piper, all in one
process — no FastAPI, no LangGraph, no ORM. The larger platform below is
**parked** (kept in the repo, not the default).

Done this round:
- [x] Streamed replies (token-by-token) for lower perceived latency
- [x] Strict Pydantic schema + retry for the analysis (`v2/coach/schema.py`, `v2/coach/analysis.py`)
- [x] Cross-session issue tracking: improved / unchanged / worse + evidence
- [x] Transcript upload and audio upload as alternate entry points
- [x] Progress view: score trends + issue tracker (`v2/coach/db.py`)
- [x] Whisper tuned for CPU (greedy decode + VAD filter)

Possible next:
- [ ] Sentence-level TTS streaming (start speaking before the full reply is generated)
- [ ] Dedupe near-duplicate issues across sessions via embedding similarity
- [ ] Silence-detection auto-stop for hands-free voice turns

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

## Future 
- [ ] Pronunciation scoring, speaking speed (WPM), pause detection
- [ ] RAG over grammar references / CEFR guidelines
- [ ] Multi-language support
- [ ] Teacher dashboard
