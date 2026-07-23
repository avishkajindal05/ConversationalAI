# ─── database/connection.py ───
"""SQLAlchemy engine and session factory.

The SQLite database file is created automatically by SQLAlchemy on first use.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from english_coach.core.settings import settings


DATABASE_URL = f"sqlite:///{settings.database_path}"

engine = create_engine(DATABASE_URL, echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def get_session():
    """Yield a database session and ensure it is closed afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
