# v2 — Communication Coach

**Status:** Active and default.

v2 is an offline communication-practice coach. A learner can have a live text
or voice conversation, upload a transcript, or upload audio. The app produces
one structured communication report and compares current performance with
issues left open from the learner's previous session.

```powershell
ollama pull llama3.2
ollama serve
streamlit run english_coach/v2/app.py
```

- [Architecture](architecture.md)
- [Data model and report contract](data-model.md)
- [v1 → v2 changes](changes.md)
- [Operations and testing](operations.md)

v2 is a local, single-user proof of concept. It prioritizes a responsive CPU
experience and reliable structured feedback over v1's multi-agent complexity.

