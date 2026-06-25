"""
Shared pytest fixtures for the test suite.

Tests run against a **real PostgreSQL** database provided by
``docker-compose.test.yml``.  Connection details come from the
same environment variables the application uses in production
(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).

**No mocking is used.**
"""

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.core.database import Base, engine
from src.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_database() -> Iterator[None]:
    """Create all tables before the session and tear them down after."""

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Flush the connection pool so each per-test event loop gets
        # fresh connections (avoids cross-loop reuse errors).
        await engine.dispose()

    async def _drop() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_create())
    yield
    asyncio.run(_drop())


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """Return a ``TestClient`` bound to the FastAPI application."""
    try:
        # Enter the context manager so every request in a test shares a single
        # event loop/portal. Without this, each request spins up its own loop
        # and reuses a pooled asyncpg connection bound to an already-closed
        # loop, raising RuntimeError on the second DB-touching request.
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Dispose the async engine's pool after each test so the next
        # test's event loop does not reuse connections bound to a closed loop.
        asyncio.run(engine.dispose())
