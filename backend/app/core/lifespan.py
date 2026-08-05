from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_config
from app.core.logging import configure_logging, get_logger
from app.db.connection import create_database_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = app.state.config if hasattr(app.state, "config") else get_config()
    configure_logging(config.log_level)
    app.state.config = config
    app.state.db_engine = create_database_engine(config)
    logger.info(
        "backend_started",
        extra={"environment": config.app_env, "port": config.backend_port},
    )
    yield
    await app.state.db_engine.dispose()
    logger.info("backend_stopped")
