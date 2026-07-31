"""Database engine and session management.

SQLite in development and tests, Postgres in production, through the same
SQLAlchemy async API. That is not a compromise — it means every repository test
runs against a real database with real constraints and real transactions, in
milliseconds, with no container to start. A test suite that needs Postgres
running is a test suite people skip.

Where the two genuinely differ (JSON operators, `pgvector`, row-level security)
the difference is called out at the point of use, and those paths are exercised
against Postgres in the deployment check rather than pretended away here.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base

log = logging.getLogger("samvaad.api.db")

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _engine_kwargs(url: str) -> dict:
    if not url.startswith("sqlite"):
        return {"pool_pre_ping": True}

    # An in-memory SQLite database lives inside its connection, so a normal pool
    # would give each session a different, empty database. StaticPool keeps one
    # connection for the whole engine, which is what makes tests coherent.
    return {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool if ":memory:" in url else None,
    }


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        kwargs = {k: v for k, v in _engine_kwargs(url).items() if v is not None}
        _engine = create_async_engine(url, echo=False, **kwargs)
        log.info("database engine created for %s", url.split("://", 1)[0])
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency. One session per request, committed or rolled back.

    Rolling back on any exception means a handler that fails halfway cannot
    leave a learner with, say, a consent row recorded but the deletion it was
    supposed to trigger never run.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_all() -> None:
    """Create the schema.

    Used in development and tests. Production uses Alembic migrations, because
    `create_all` cannot alter an existing table and will silently do nothing
    when a column has been added — which looks exactly like success.
    """
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def dispose() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
