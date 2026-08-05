from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.core.config import AppConfig


def create_database_engine(config: AppConfig) -> AsyncEngine:
    return create_async_engine(config.sqlalchemy_database_url, pool_pre_ping=True)


def create_session_factory(config: AppConfig) -> async_sessionmaker:
    return async_sessionmaker(create_database_engine(config), expire_on_commit=False)
