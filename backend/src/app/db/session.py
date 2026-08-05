from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def create_engine(database_url: str, pool_size: int, max_overflow: int) -> AsyncEngine:
    return create_async_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


def configure_database(database_url: str, pool_size: int, max_overflow: int) -> None:
    global _engine, _session_factory
    _engine = create_engine(database_url, pool_size=pool_size, max_overflow=max_overflow)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database engine is not configured.")
    return _engine


async def get_db() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database session factory is not configured.")

    session = _session_factory()
    try:
        yield session
    finally:
        await session.close()


get_session = get_db


async def check_database() -> None:
    async with get_engine().connect() as connection:
        await connection.execute(text("select 1"))


async def dispose_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
