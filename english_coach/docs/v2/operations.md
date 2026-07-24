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
```

## Coverage

- Schema tests cover score coercion, strict output checks, and issue carry-forward.
- Database tests cover persistence and open-issue retrieval.
- Analysis tests cover valid output, retries, and safe failures.

## Known limitations

- SQLite is for a local proof of concept, not concurrent multi-user writes.
- Issue matching is exact-description matching; similar wording is not deduplicated.
- Voice input is push-to-talk rather than full duplex.
- Piper starts after the reply completes; sentence-level TTS streaming is future work.

