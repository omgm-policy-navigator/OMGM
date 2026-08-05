from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import AppConfig
from app.core.logging import configure_logging, get_logger
from app.db.session import configure_database, dispose_database
from app.modules.policies import load_policy_seed

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    config = getattr(app.state, "config", None) or AppConfig.from_env()
    configure_logging(config.log_level)
    configure_database(
        config.database_url,
        pool_size=config.database_pool_size,
        max_overflow=config.database_max_overflow,
    )
    app.state.policy_catalog = load_policy_seed(config.policy_seed_dir)
    app.state.config = config
    logger.info(
        "backend_started",
        extra={
            "environment": config.app_env,
            "port": config.backend_port,
            "policy_count": len(app.state.policy_catalog.policies),
        },
    )
    try:
        yield
    finally:
        await dispose_database()
        logger.info("backend_stopped")
