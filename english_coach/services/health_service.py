# ─── services/health_service.py ───
"""Dependency health checks for the /health endpoint.

Each check is lightweight (no full model loads) and never raises - it
reports a per-component status so the endpoint can show what is and isn't
available without falling over.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import text

from english_coach.core.logger import logger
from english_coach.core.settings import settings


def _check_ollama() -> dict[str, Any]:
    """Ollama reachable, and the configured models present."""
    wanted = {settings.conversation_model, settings.scoring_model, settings.reasoning_model}
    try:
        resp = httpx.get(f"{settings.ollama_host}/api/tags", timeout=3.0)
        resp.raise_for_status()
        available = {m["name"] for m in resp.json().get("models", [])}
    except Exception as e:
        return {"ok": False, "error": f"unreachable: {e}"}

    # Ollama tags are like "qwen3:8b"; match on the base name too.
    def _present(name: str) -> bool:
        return any(a == name or a.split(":")[0] == name.split(":")[0] for a in available)

    missing = sorted(m for m in wanted if not _present(m))
    return {"ok": not missing, "missing_models": missing, "models_present": sorted(available)}


def _check_sqlite() -> dict[str, Any]:
    try:
        from english_coach.database.connection import engine

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "path": settings.database_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_whisper() -> dict[str, Any]:
    try:
        import faster_whisper  # noqa: F401

        return {"ok": True, "model": settings.whisper_model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _check_piper() -> dict[str, Any]:
    try:
        import piper  # noqa: F401
    except Exception as e:
        return {"ok": False, "error": str(e)}
    model_file = Path("data/models/piper") / f"{settings.piper_model}.onnx"
    return {
        "ok": True,
        "model": settings.piper_model,
        "downloaded": model_file.exists(),
    }


def run_health_checks() -> dict[str, Any]:
    """Run every dependency check and summarise overall status."""
    components = {
        "ollama": _check_ollama(),
        "sqlite": _check_sqlite(),
        "whisper": _check_whisper(),
        "piper": _check_piper(),
    }
    # Ollama + SQLite are required to serve a session; speech is optional
    # (text chat still works without it).
    critical_ok = components["ollama"]["ok"] and components["sqlite"]["ok"]
    status = "healthy" if all(c["ok"] for c in components.values()) else (
        "degraded" if critical_ok else "unhealthy"
    )
    if status != "healthy":
        logger.warning("Health check status=%s components=%s", status, components)
    return {"status": status, "components": components}
