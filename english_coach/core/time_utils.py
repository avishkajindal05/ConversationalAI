# ─── core/time_utils.py ───
"""Time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC 'now'.

    Replaces the deprecated ``datetime.utcnow()`` while keeping the same
    naive-UTC representation the ORM columns and existing rows use.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
