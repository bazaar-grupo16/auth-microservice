"""
SQLAlchemy engine, session factory, and declarative base.

The connection string is built from environment variables via
:pymod:`src.core.config` — no credentials appear in this file.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import get_settings


settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def check_db_connection() -> bool:
    """
    Attempt a lightweight query against the database.

    Returns
    -------
    bool
        ``True`` if the database is reachable, ``False`` otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
