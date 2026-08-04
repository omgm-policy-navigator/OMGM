from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import AppConfig
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = AppConfig.from_env()
    configure_logging(config.log_level)
    app.state.config = config
    logger.info("backend_started", extra={"environment": config.app_env, "port": config.backend_port})
    yield
    logger.info("backend_stopped")
