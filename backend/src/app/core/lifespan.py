from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import AppConfig
from app.core.logging import configure_logging, get_logger
from app.db.session import configure_database, dispose_database

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = AppConfig.from_env()
    configure_logging(config.log_level)
    configure_database(
        config.database_url,
        pool_size=config.database_pool_size,
        max_overflow=config.database_max_overflow,
    )
    app.state.config = config
    logger.info("backend_started", extra={"environment": config.app_env, "port": config.backend_port})
    try:
        yield
    finally:
        await dispose_database()
        logger.info("backend_stopped")
