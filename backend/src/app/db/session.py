from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DEFAULT_DATABASE_URL = "postgresql+asyncpg://marry_policy:marry_policy@localhost:5432/marry_policy"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)


def configure_database(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_engine(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    if _engine is None:
        configure_database(DEFAULT_DATABASE_URL)
    if _engine is None:
        raise RuntimeError("Database engine is not configured.")
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        get_engine()
    if _session_factory is None:
        raise RuntimeError("Database session factory is not configured.")
    async with _session_factory() as session:
        yield session


async def check_database() -> None:
    async with get_engine().connect() as connection:
        await connection.execute(text("select 1"))


async def dispose_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
