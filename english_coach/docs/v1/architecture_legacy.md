# v1 architecture (legacy)

> This document describes the parked FastAPI/LangGraph platform. For the
> active single-process Communication Coach, see the [v2 architecture](../v2/architecture.md).

## Overview
English Coach is an offline Agentic AI English Speaking Coach. Conversation,
planning, evaluation, and long-term learning are separate responsibilities,
each owned by specialized LangGraph agents. Agents share LLM instances by
role rather than each loading their own model:

| Purpose | Model (Ollama) | Setting |
|---|---|---|
| Conversation graph (dialogue) | `qwen3:8b` | `CONVERSATION_MODEL` |
| Evaluation scoring — grammar, vocabulary, fluency, engagement, confidence | `llama3.2` (lighter/faster) | `SCORING_MODEL` |
| Evaluation reasoning — recommendation, report | `qwen3:8b` | `REASONING_MODEL` |

The lighter model does the mechanical scoring; the larger model is reserved
for the reasoning-heavy generation. Ollama lazily loads/evicts whichever
model is actually in use, so only one large model is resident at a time.

## Two graphs

### Conversation Graph (`graphs/conversation_graph.py`)
Runs once per user turn.

```
                (turn 0 only)
START ──▶ [route] ──▶ Greeting Agent ──▶ Difficulty Planner ──▶ Conversation Agent ──▶ Memory Manager ──▶ END
      └──────────────────────────────▶ (turn > 0, skips Greeting) ───────────────────────┘
```

- **Greeting Agent** (`agents/conversation/greeting.py`) — only runs on turn 0. Builds opening instructions from the learner profile (level, goal, a recommended topic).
- **Difficulty Planner** (`agents/conversation/planner.py`) — every turn. Turns the learner's CEFR level + known weak spots into vocabulary/grammar guidance for the Conversation Agent.
- **Conversation Agent** (`agents/conversation/conversation_agent.py`) — the teacher. Never evaluates or corrects; just keeps the conversation going, informed by the planner's guidance.
- **Memory Manager** (`agents/conversation/memory.py`) — persists new transcript turns to SQLite and advances `turn_count`.

### Evaluation Graph (`graphs/evaluation_graph.py`)
Runs once, after the session ends, over the full transcript. The five
scoring agents are independent and **fan out in parallel**; Recommendation
and Report depend on all of them and run at the fan-in.

```
START ─┬─ Grammar ────┐
       ├─ Vocabulary ─┤
       ├─ Fluency ────┼─▶ Recommendation ─▶ Report ─▶ END
       ├─ Engagement ─┤
       └─ Confidence ─┘
```

Each scoring agent (`agents/evaluation/*.py`) calls the scoring LLM with its
own rubric and parses a strict-JSON response (with a safe fallback if
parsing fails, so one flaky agent can't crash the graph). The five scorers
return **partial `{"scores": {...}}` updates** that merge into the
`SessionState.scores` channel via a reducer (`memory/session_state.py:
merge_scores`) — this is what makes concurrent fan-in safe instead of
raising `InvalidUpdateError`. The Report agent computes a weighted overall
score and asks the reasoning LLM for a narrative summary.

> On a single-GPU/CPU host Ollama may still serialize the model calls, so the
> wall-clock win comes mostly from the lighter `SCORING_MODEL`; the parallel
> topology is ready to exploit real concurrency given better hardware or
> multiple model instances.

`services/session_service.py` orchestrates both graphs, persists the report,
and updates the learner's profile after every session.

## Node-level optimizations
- **Recommendation** derives the next-session goal deterministically in Python from the score thresholds (`derive_goal`), then asks the LLM only for homework/exercises/topics — from the numeric scores, never re-reading the transcript.
- **Report** computes the weighted overall score in Python and passes only a compact score digest to a **capped-length `llama3.2`** call (it is writing, not reasoning). This removed the two slowest `qwen3:8b` generations from the critical path.
- **Resilience** — every LLM call is retried (`with_retry`) and time-bounded (`client_kwargs` timeout); evaluation agents fall back to a safe default dict on failure so the graph always completes.
- **Observability** — each graph node is wrapped by `timed_node` (`graphs/base_graph.py`), logging per-node wall-clock time.

## Components
- **Frontend** — Streamlit UI (`frontend/pages/home.py`): session start/end, text + voice chat, streamed evaluation progress (`st.status`), report view.
- **Backend** — FastAPI (`backend/main.py`): `/health` (dependency checks), `/session/start`, `/chat`, `/voice/chat`, `/session/{id}/end`, `/session/{id}/end/stream` (NDJSON progress).
- **Workflow Engine** — LangGraph orchestrates the two graphs above.
- **LLM** — Ollama, three roles across two models (see the table above): `llm/conversation_model.py` (conversation) and `llm/evaluation_model.py` (scoring + reasoning; the model is selectable per agent via its constructor).
- **Speech-to-Text** — Faster Whisper (`speech/speech_to_text.py`).
- **Text-to-Speech** — Piper (`speech/text_to_speech.py`).
- **Database** — SQLite via SQLAlchemy (`database/models.py`, `database/dao/`): users, sessions, messages, learner_profiles, reports.
- **Learner Profile** — `memory/learner_profile.py` (pydantic model) + `services/profile_service.py` (load/save via `LearnerDAO`). This is the only piece of state that survives across sessions.
- **SessionState** — `memory/session_state.py`. The in-memory source of truth while a session is active; SQLite is persistence, not communication between agents.

## Package layout
```
english_coach/
├── core/          — settings, config, logging, constants, exceptions, time_utils
├── database/      — SQLAlchemy models, connection, DAOs
├── memory/        — session state, learner profile, conversation memory, checkpoints
├── services/      — profile_service, session_service (orchestration), health_service
├── llm/           — conversation/evaluation model wrappers
├── speech/        — STT and TTS wrappers
├── agents/
│   ├── conversation/  — greeting, planner, conversation_agent, memory
│   └── evaluation/    — grammar, vocabulary, fluency, engagement, confidence, recommendation, report
├── graphs/        — conversation_graph.py, evaluation_graph.py
├── prompts/       — prompt templates
├── frontend/      — Streamlit pages
├── backend/       — FastAPI application
├── reports/       — generated reports, exports, templates
├── tests/         — unit / integration / e2e
├── docs/          — documentation
├── config/        — YAML configuration files
└── data/          — runtime data (SQLite DB created here)
```

## Testing
`tests/` holds mock-based unit and integration tests that run without a live
Ollama server or the real database:
- `tests/unit/test_pure_functions.py` — reducers, goal derivation, weighted score, JSON-fallback parsing.
- `tests/unit/test_dao.py` — DAO round-trips against an isolated temp SQLite (via the `db_session` fixture in `tests/conftest.py`).
- `tests/integration/test_conversation_graph.py` — conversation graph turns with a mocked conversation LLM (greeting-on-turn-0 routing, turn counter).
- `tests/integration/test_evaluation_graph.py` — parallel scoring fan-in, recommendation/report aggregation, and graph completion under LLM failure.
- `tests/integration/test_profile_update.py` — evaluation output mapped onto the learner profile.

Run them with:
```bash
pytest english_coach/tests -q
```
