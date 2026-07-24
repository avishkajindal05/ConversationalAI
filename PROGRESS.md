# English Coach — Progress Report

**Project:** Offline AI English Speaking Coach
**Prepared for:** Founders / project sponsors
**Date Started:** 22 July 2026
**Overall status:** 🟡 **Working prototype** — the full voice loop runs end-to-end on a local machine. A few polish bugs and one UI blocker remain; core AI pipeline is functional.

---

## 1. What I'm building

An **offline, privacy-preserving AI coach that helps people practise spoken English.** The learner has a natural voice conversation with the bot; when they finish, the system evaluates their English and returns structured feedback and a downloadable report. Everything runs on open-source models locally — **no cloud APIs, no data leaving the machine.**

The pipeline is:

```
🎤 Microphone → Speech-to-Text (Whisper) → LLM (Ollama) → Text-to-Speech (Piper) → 🔊 Spoken reply
```

There are **two delivery surfaces** in the codebase:

| Surface | What it is | Intended use |
|---|---|---|
| **Full app** | Streamlit UI + FastAPI backend + LangGraph workflow + SQLite | The complete product: multi-agent conversation, scoring, progress dashboard, PDF reports |
| **Voice Bot** (`voice_bot.py`) | A single-process, dependency-light Streamlit app | A fast, self-contained demo of the voice loop with end-of-chat feedback |

---

## 2. Architecture (how it fits together)

| Layer | Technology | Notes |
|---|---|---|
| Frontend | **Streamlit** | Practice page (text + voice), progress dashboard, report view |
| Backend API | **FastAPI** | Session lifecycle, `/voice/chat`, streaming evaluation |
| Workflow engine | **LangGraph** | Orchestrates conversation + evaluation as graphs |
| Language models | **Ollama** — `qwen3:8b` (conversation + reasoning), `llama3.2` (lightweight scoring) | Runs fully offline |
| Speech-to-text | **Faster-Whisper** (`small`) | Transcribes learner audio |
| Text-to-speech | **Piper** (`en_US-lessac-medium`) | Speaks the coach's replies |
| Storage | **SQLite + SQLAlchemy** | Session records, learner profiles |
| Config | **Pydantic Settings + YAML/.env** | Model names, hosts, paths |

---

## 3. What is working ✅

These were **verified running on the target machine this session** (not just "the code exists"):

- **Model setup** — Both Ollama models (`qwen3:8b`, `llama3.2`) pull and load correctly.
- **Backend boots** — FastAPI starts, loads STT/TTS services, health check passes.
- **Speech-to-Text** — Whisper transcribes recorded audio accurately (e.g. *"yes today it rained so I went out in the rain and danced for a little bit"*).
- **Conversation** — The LLM produces natural, in-character coaching replies and asks follow-up questions.
- **Text-to-Speech** — Piper synthesizes spoken audio (fixed this session — see §4).
- **Full voice round-trip** — Record → transcribe → LLM reply → spoken audio playback works end-to-end.
- **Voice recorder UX** — After each turn the mic resets to a fresh "Record" button (fixed this session — see §4).
- **Feedback generation (in isolation)** — The end-of-conversation coaching feedback LLM call returns correct, well-structured output (`Overall` / `What went well` / `Suggestions`) in ~7 seconds when tested directly.

**Now verified end-to-end (QA pass, 23 July):**

- **Full evaluation pipeline** — Ran the real evaluation graph through Ollama on a sample transcript: all five scorers + recommendation + report finished in **51 seconds on CPU** and produced a valid, complete report (overall score, per-skill scores, strengths/weaknesses, next-step recommendations).
- **PDF report export** — Generated a real PDF from that report; it renders cleanly with all sections.
- **Progress dashboard data path** — Seeded sessions into the database and read them back through the dashboard service: correct row shape, correct oldest-first ordering, and the score-trend/delta calculations the dashboard charts all check out.
- **Automated tests** — Full suite green (**23 passed**), plus GitHub Actions CI.

**Verified LIVE in the full app (23 July):** Ran the complete application on CPU and held two real voice conversations with the coach, end to end — mic → transcription → spoken coach reply → **End session → evaluation report + PDF → progress dashboard** tracking both sessions' trends. Everything worked.

**Grammar grader — QA finding FIXED and validated live ✅**
- *Was:* the grammar scorer used a cold "give a score" prompt and rated error-riddled learner speech **82/100** — undifferentiated and too lenient for a coaching product.
- *Now:* a strict **two-step prompt** (list every error, *then* score against an explicit rubric). Validated across the two live sessions — grammar scored **54** for the weaker session and **84** for the stronger one, and correctly drove the recommendation (low grammar → past-tense narration homework). LanguageTool is wired in as an optional, offline, best-effort source of *verified* corrections (never affects the score).
- Second QA finding (bare-label strengths/weaknesses) also cleared — the report now returns proper phrases ("Grammar skills need improvement", "Building confidence").

**Performance decision applied (CPU):** the full app's conversation model was switched from `qwen3:8b` (~60s/turn, and it timed out cold-loading) to **`llama3.2`** via `.env`. The entire app now runs on one small model — **~6–7s per turn, session start in 6s**, and no memory-thrashing model swaps. Reversible by editing `.env`.

---

## 4. Blockers 🚧

### B1 — Voice Bot "End conversation & get feedback" produced no visible output ✅ FIXED (pending your verification)
- **Severity:** High (it's the headline feature of the priority surface)
- **Root cause:** The feedback *generation* was fine all along (verified ~7s, correct format). The bug was **UI visibility**: the feedback and its spinner rendered at the *top* of the page, but after recording, the user is scrolled to the *bottom* at the mic — so it appeared off-screen and looked like "nothing happened."
- **Fix applied:** Feedback now opens in a **centred modal dialog** that is impossible to miss regardless of scroll position, and it's generated *inside* the dialog so the "analysing…" state is always on-screen. Any error now surfaces in the modal instead of failing silently. A copy also stays on the page to re-read after closing.
- **To confirm:** Run the Voice Bot alone, have a short chat, click **End conversation & get feedback** → the feedback modal should pop up and fill in within a few seconds.

### B2 — Latency on CPU (constraint, being optimised — not a defect)
- **Severity:** Medium
- **Decision context:** CPU-only is a given (no GPU); offline is required, but a **hosted open-source model is permitted**.
- **Observed:** The **priority voice surface already uses `llama3.2` (3.2B)** → replies and feedback in **~7s**, which is acceptable. The slow numbers (~45–65s/turn, minutes for evaluation) belong to the *full app's* `qwen3:8b`.
- **CPU-appropriate levers (no GPU needed):**
  1. Keep the voice surface on the small model (`llama3.2`) — already done.
  2. For the full app, consider a smaller conversation model, quantisation, and shorter generation caps.
  3. **Optional speed escape hatch that stays open-source:** allow an opt-in **hosted open-source model** (e.g. Llama served via a fast inference provider) for near-instant replies when a network is available, defaulting back to fully-offline Ollama. Satisfies "offline required, hosted-open-source allowed."
  4. Pre-warm models on startup; keep clear "thinking…" UX.

### B3 — Sessions are stored in memory (dev friction + no persistence)
- **Severity:** Medium
- **Behaviour:** The backend keeps live sessions in an in-memory dictionary. **Restarting the backend (which auto-reloads on every code edit in dev) invalidates all active sessions** and returns a `404`. It also means sessions don't survive a crash and won't scale beyond one process.
- **Impact today:** Mostly developer friction — after any code change you must start a new session. For production it needs a persistent/shared session store.

### B4 — Two apps + two models contend for one machine
- **Severity:** Low–Medium
- Running the full app and the Voice Bot simultaneously (or the two Ollama models together) can thrash CPU/RAM and cause model reloads. Feeds directly into B1 and B2. Recommend running **one surface at a time** during demos.

---

## 5. Realistic timeline to clear the blockers

Estimates assume one developer, and are **calendar-realistic** (not best-case):

| Blocker | Effort | ETA |
|---|---|---|
| **B1** — Voice Bot feedback | ✅ Fix applied (modal dialog); needs your click-through to confirm | **Done — verify** |
| **B2** — Latency on CPU | Voice surface already fast (~7s on `llama3.2`); optional hosted-open-source escape hatch for the full app | **~1 day** for the optional toggle |
| **B3** — Persistent sessions | Move session state to SQLite; reload learner state on demand | **1–2 days** |
| **B4** — Resource contention | Operational — run one surface at a time; optional launch script | **0.5 day** |
| **QA pass** on evaluation, PDF, dashboard | ✅ Done — pipeline, PDF, and dashboard data path all verified end-to-end | **Done** |
| **Quality tuning** — grammar grader + report phrasing (QA findings) | Stronger/rules-based grammar signal; prompt-tune strengths/weaknesses | **1–2 days** |

**Bottom line (given CPU-only, voice-first, offline-required / hosted-open-source-allowed):**
- ✅ The **priority voice demo works today** on CPU (~7s replies + feedback) once you confirm the B1 fix.
- 🟢 A **polished, reliable voice demo** (persistence + QA pass) → **~2–3 days.**
- 🟢 Optional **hosted-open-source speed toggle** for the full app → **+1 day**, keeps offline as the default.

---

