# v1 — Legacy agentic English Coach

**Status:** Parked. This is not the default application path.

v1 is the original full-platform design. It uses a Streamlit frontend, a
FastAPI backend, LangGraph conversation and evaluation workflows, SQLAlchemy,
and a normalized SQLite schema. It supports voice/text practice, PDF reports,
and a learner-progress dashboard.

```powershell
uvicorn english_coach.backend.main:app
streamlit run english_coach/frontend/streamlit_app.py
```

- [Architecture summary](architecture.md)
- [Detailed original architecture](architecture_legacy.md)
- [HTTP API reference](api.md)
- [Prompt notes](prompts.md)
- [Development log](development-log.md)
- [Full development roadmap](roadmap.md)

For the maintained application, use [v2](../v2/README.md).

