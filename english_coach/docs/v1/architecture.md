# v1 architecture summary

```text
Streamlit multipage UI
        |
        v
FastAPI backend
        |
        +--> Conversation LangGraph
        |      greeting -> difficulty planner -> conversation -> memory
        |
        +--> Evaluation LangGraph
               five scoring agents -> recommendation -> report
        |
        v
SQLAlchemy / SQLite
```

The v1 backend holds active `SessionState` objects in memory, while SQLite
persists users, messages, learner profiles, sessions, and reports. This design
is kept for reference; v2 replaces it with a lower-latency transcript-in,
structured-report-out pipeline.

