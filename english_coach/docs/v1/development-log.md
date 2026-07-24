# v1 development log (legacy)

> This log records the parked v1 platform. Active changes are documented in
> [v2 changes](v2/changes.md).

A chronological record of every significant change to English Coach, why it
was made, and (where relevant) what failed and how it was fixed. Read this
alongside [architecture.md](architecture.md) (current design) and
[roadmap.md](roadmap.md) (status).

---

## 1. Starting point

The repository began as a scaffold with working plumbing but mostly stubs:

- Text chat and voice chat (STT → single LLM turn → TTS) already worked end
  to end through one `ConversationAgent`.
- `graphs/evaluation_graph.py` raised `NotImplementedError`.
- `graphs/conversation_graph.py` was a single node.
- All DAOs (`learner_dao`, `session_dao`, `report_dao`) raised
  `NotImplementedError`.
- `LearnerProfile` was 7 flat fields.
- `/chat` and `/voice/chat` were **stateless** (the whole message history was
  posted every turn; no session concept, no persistence).

The goal was to turn this into an **agentic language-learning platform**:
separate conversation, planning, evaluation, and long-term learning into
specialized agents across two LangGraph graphs.

---

## 2. Architecture build-out

| Area | Before | After | Why |
|---|---|---|---|
| Conversation graph | 1 node | Greeting → Difficulty Planner → Conversation → Memory, with conditional routing (Greeting only on turn 0) | Separation of concerns; adapt difficulty per learner; persist transcript |
| Evaluation graph | stub (`NotImplementedError`) | 7 agents: Grammar, Vocabulary, Fluency, Engagement, Confidence, Recommendation, Report | Independent, explainable assessment after the session |
| Database | stub DAOs | ORM models (`users`, `sessions`, `messages`, `learner_profiles`, `reports`) + full DAOs | Real persistence |
| Learner profile | 7 flat fields | Nested model (grammar/vocabulary/engagement/confidence/recommendation + history) + `ProfileService` | Cross-session personalization |
| Session lifecycle | stateless `/chat` | `SessionService` + in-memory registry; `/session/start`, `/chat`, `/voice/chat`, `/session/{id}/end` | SessionState is the in-memory source of truth; SQLite is persistence, not agent-to-agent communication |

---

## 3. Model decisions (the core of this log)

### 3.1 One model, two roles (not two model instances)
**Initial design:** two separate Qwen3 8B instances (a "Conversation LLM" and
an "Evaluation LLM").
**Changed to:** a single Qwen3 8B weight set that Ollama lazily loads/evicts,
used in two roles.
**Why:** on a 16 GB / 4 GB-VRAM laptop, holding two 8B models (≈5–6 GB each)
alongside Whisper + Piper + Streamlit + FastAPI risks exhausting RAM. Since the
evaluation graph only runs *after* the conversation ends, the two never need
to be resident simultaneously — Ollama's own `keep_alive` eviction handles it,
so no manual load/unload code was needed.

### 3.2 Per-agent evaluation models
**Before:** all 7 evaluation agents used `qwen3:8b`, run **sequentially**.
**Change:** introduced two roles in `settings.py`:
- `SCORING_MODEL = llama3.2` (lighter/faster) for the 5 mechanical scorers.
- `REASONING_MODEL = qwen3:8b` for recommendation + report.

Removed the old single `EVALUATION_MODEL` setting; updated `.env`,
`.env.example`, `models.yaml`.
**Why:** scoring (grammar/vocabulary/…) is mechanical and doesn't need an 8B
reasoning model; a 3B model is 3–4× faster with comparable rubric scoring.

### 3.3 Report → light model
**Before:** Report on `qwen3:8b`.
**After:** Report on `llama3.2` with a capped output length (`num_predict`).
**Why:** the overall score is computed in Python (weighted mean); the LLM only
*writes* a summary. Writing ≠ reasoning, so the light model suffices.
**Result:** Report node dropped from ~173s to ~22s (≈8×).

### 3.4 Recommendation → light model
**Before:** Recommendation on `qwen3:8b`.
**After:** Recommendation on `llama3.2`.
**Why:** the next-session goal is now derived deterministically in Python
(`derive_goal`, threshold rules), so the LLM only writes homework/exercises —
again writing, not reasoning.
**Result:** Recommendation node dropped from ~164s to ~8s.

### 3.5 Key insight — prompt size wasn't the bottleneck
When Recommendation was first optimized, its **prompt** was shrunk (transcript
dropped, only scores passed). That barely moved its latency, because
`qwen3:8b`'s cost is dominated by **output generation** (Qwen3 runs a hidden
"thinking" pass), not input size. The real speed-up only came from **switching
the model**. Report proved the same point (switching model = 8× faster). This
is why the final answer for both nodes was "move to `llama3.2`," not "trim the
prompt."

### 3.6 Config note
- `conversation_model` default is `qwen3:8b-instruct-q4`, but `.env` overrides
  it to `qwen3:8b` (the tag actually pulled on the dev machine). A mismatch
  between `.env` and `models.yaml` was flagged and the values aligned.
- After 3.4, **`REASONING_MODEL` (`qwen3:8b`) is no longer used by any
  evaluation agent** — all evaluation now runs on `llama3.2`. The setting is
  retained for flexibility (e.g., swapping a specific agent back to an 8B
  model), but it is currently dormant.

**Final model configuration:** Conversation → `qwen3:8b`; all evaluation
agents → `llama3.2`.

---

## 4. Evaluation latency journey

Measured on the same fixed transcript each time (i7-9750H / GTX 1650, CPU
inference), so the numbers are comparable.

| Stage | Eval time | What changed |
|---|---|---|
| Original | **1322.7s** | 7 agents, all `qwen3:8b`, sequential |
| Round 1 | **397.2s** | 5 scorers → `llama3.2`; parallel fan-out/fan-in |
| Round 2 | **226.2s** | Report → `llama3.2` + capped; Recommendation prompt shrunk |
| Round 3 | **48.1s** | Recommendation → `llama3.2` |

Final per-node breakdown (48s run): 5 scorers ~40s (parallel, bounded by the
slowest), Recommendation ~8s, Report ~8s. **≈27× faster than the original.**

---

## 5. Parallelizing the evaluation graph

**Before:** Grammar → Vocabulary → Fluency → Engagement → Confidence →
Recommendation → Report (linear).
**After:** the 5 scorers fan out from START in parallel and fan in to
Recommendation → Report.

**The risk:** in LangGraph, multiple nodes writing the same state channel in
one super-step raise `InvalidUpdateError` unless that channel has a **reducer**.
**The fix:**
- Added a top-level `SessionState.scores` channel annotated with a
  `merge_scores` reducer (dict merge).
- Moved `scores` out of the nested `EvaluationState` (reducers apply to
  top-level channels only).
- The 5 scorers now **return partial `{"scores": {...}}` updates** instead of
  mutating and returning the whole state.

**De-risking:** before touching the real agents, a throwaway script confirmed
fan-out/fan-in + reducer works on a Pydantic-model state in the installed
LangGraph (1.2.9). Only then were the agents refactored.

**Honest caveat:** on a single-GPU/CPU host, Ollama serializes the model
calls, so the wall-clock win came mostly from the lighter model, not true
concurrency. The **graph topology** is now ready to exploit real parallelism
given better hardware or multiple model instances.

---

## 6. Robustness & observability

- **Retry + timeout** on every LLM call (`with_retry` + `client_kwargs`
  timeout). The conversation model returns a friendly fallback message on
  failure; evaluation agents fall back to a safe default dict so one flaky
  call never crashes the graph.
- **`/health`** now verifies dependencies: Ollama reachable + required models
  present, SQLite connectable, Whisper and Piper importable/configured.
  Returns 503 only when a *critical* dependency (Ollama or SQLite) is down.
- **Per-node timing logs** via a `timed_node` wrapper applied in both graphs.
- **Streaming evaluation progress**: `/session/{id}/end/stream` (NDJSON) emits
  a progress event as each agent finishes; the Streamlit `st.status` widget
  shows the stages during the (previously silent) wait.

---

## 7. Phase 7 — polish

- **Multipage app** (`st.navigation`): a Practice page and a Progress page,
  replacing the single `home.py`.
- **Dashboard**: `/users/{id}/history` + `dashboard_service` assemble a
  learner's evaluated sessions; the Progress page shows metrics, score-trend
  line charts, and a history table.
- **PDF export**: `reports/pdf_report.py` builds a report PDF (fpdf2), exposed
  as a download button on the report view.
- **Typing effect**: assistant replies stream word-by-word via
  `st.write_stream`. (True token streaming through LangGraph is logged as
  future work.)
- **CI**: `.github/workflows/ci.yml` runs pytest on push/PR using a lean
  `requirements-test.txt` (no heavy speech deps, which the tests never import).
- **Non-blocking backend**: the route handlers that do blocking work
  (LLM/DB/dependency probes) were changed from `async def` to sync `def` so
  FastAPI runs them in its threadpool. Before this, a single worker blocked on
  a long LLM call would stall `/health`, the dashboard, and any second user.

---

## 8. Bugs & fixes encountered

| Symptom | Root cause | Fix |
|---|---|---|
| `uvicorn ... backend.api.main` failed | README pointed at a module that doesn't exist | Corrected to `backend.main`; added full run instructions |
| Measurement script: `ModuleNotFoundError: english_coach` | Running a script by absolute path puts the *script's* dir on `sys.path`, not the cwd | `sys.path.insert(project_root)` in the script |
| `UnicodeEncodeError` on emoji in LLM output | Windows console defaults to cp1252 | Wrapped stdout in a UTF-8 writer (test scripts only) |
| `st.status` progress not rendering | Streamlit callbacks (`on_click`) cannot paint UI | Moved start/end work out of the callback into the main script body via a pending-flag pattern |
| PDF: "Not enough horizontal space to render a single character" | fpdf2 `multi_cell` defaults to `new_x=RIGHT`, leaving the cursor at the right margin; two consecutive `multi_cell`s then have zero width | Added a `_para` helper that passes `new_x="LMARGIN"` |
| `datetime.utcnow()` deprecation warnings | Deprecated in Python 3.12+ | `core/time_utils.utcnow()` helper (naive UTC), routed all call sites through it |
| `/health` and dashboard hung during a chat | `async def` handlers ran blocking LLM code on the event loop | Converted blocking handlers to sync `def` (threadpool) — see §7 |
| `InvalidUpdateError` (anticipated) | Concurrent writes to a channel without a reducer | Pre-empted with the `merge_scores` reducer + de-risk test — see §5 |

---

## 9. Testing

23 mock-based tests (no live Ollama, no real DB) under `english_coach/tests`:
- Pure functions: reducer, goal derivation, weighted score, JSON-fallback.
- DAO round-trips against a temp SQLite (`db_session` fixture).
- Conversation graph turns (greeting-on-turn-0 routing, turn counter).
- Evaluation graph (parallel fan-in, aggregation, completion under LLM failure).
- Profile-update mapping and dashboard history assembly.
- PDF builder (valid, non-empty, non-latin1-safe).

---

## 10. Dependencies & tooling added

- `fpdf2` — PDF report generation.
- `requirements-test.txt` — minimal test dependency set for CI.
- `.vscode/launch.json` + `settings.json` — one-click Backend + Frontend run,
  pinned to the project `.venv` (avoids the Anaconda-interpreter trap).

---

## 11. Current state (summary)

- **Conversation** on `qwen3:8b`; **all evaluation** on `llama3.2`.
- Evaluation ≈ 48s (was 1322s).
- Two LangGraph graphs, 11 agents, parallel scoring.
- Session lifecycle with SQLite persistence + evolving learner profile.
- Multipage Streamlit UI with progress dashboard, PDF export, streamed
  evaluation progress, and typing-effect chat.
- 23 passing tests + CI.
