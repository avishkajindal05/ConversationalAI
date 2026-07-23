# ─── tests/conftest.py ───
"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from english_coach.database.connection import Base
# Importing models registers the tables on Base.metadata.
import english_coach.database.models  # noqa: F401


@pytest.fixture()
def db_session(tmp_path):
    """An isolated SQLite database session backed by a temp file."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
