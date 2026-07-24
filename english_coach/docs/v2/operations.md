# v2 operations and testing

## Prerequisites

- Python 3.11+
- Ollama at `http://localhost:11434` with `llama3.2`
- Optional microphone and Piper voice files for voice mode

Settings are read from `.env` through `core/settings.py`. v2 uses the voice
model, Ollama host, Whisper model, and Piper model settings.

## Commands

```powershell
streamlit run english_coach/v2/app.py
.venv\Scripts\python.exe -m pytest english_coach/tests -q

# Populate demo users with real multi-session conversations and reports
.venv\Scripts\python.exe -m english_coach.v2.seed_demo --reset
```

## Demo data

`seed_demo.py` creates three candidates — `priya_demo` (steady improver),
`rahul_demo` (a rambler whose clarity issue eases over time), and `sara_demo`
(consistently strong) — by running the real analysis pipeline across several
sessions each. Enter one of those IDs in the app and open **Progress** to see
score trends and the issue tracker. `--reset` clears only those demo IDs first,
so the script is safe to re-run and never touches real learner rows.

## Coverage

- Schema tests cover score coercion, strict output checks, and issue carry-forward.
- Database tests cover persistence and open-issue retrieval.
- Analysis tests cover valid output, retries, and safe failures.

## Known limitations

- SQLite is for a local proof of concept, not concurrent multi-user writes.
- Issue matching is exact-description matching; similar wording is not deduplicated.
- Voice input is push-to-talk rather than full duplex.
- Piper starts after the reply completes; sentence-level TTS streaming is future work.

