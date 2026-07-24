# v1 → v2 changes

| Area | v1 | v2 |
| --- | --- | --- |
| Runtime | Streamlit + FastAPI | One Streamlit process |
| Orchestration | Two LangGraph workflows | Direct function pipeline |
| Analysis | Five scorers + recommendation + report calls | One structured Ollama call |
| Persistence | SQLAlchemy, normalized SQLite | `sqlite3`, one table with JSON columns |
| History | Learner-profile score history | Improved / unchanged / worse issue verdicts |
| Inputs | Live text and voice | Live text, voice, transcript upload, audio upload |

## v2 additions

- Streamed conversation replies.
- Optional Piper TTS, disabled by default.
- Faster-Whisper CPU tuning: greedy decoding and voice-activity filtering.
- Pydantic validation with retries for analysis output.
- Strict completeness checks for metrics and prior issue verdicts.
- Cross-session issue tracking, trends, and transcript download.

The FastAPI/LangGraph platform remains in the repository as [v1](../v1/README.md).
It is not the default demo path.

