import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import AppConfig
from app.core.logging import configure_logging, get_logger
from app.db.session import configure_database, dispose_database, get_db
from app.modules.policies import load_policy_seed
from app.modules.sessions.service import cleanup_expired_sessions

logger = get_logger(__name__)


async def cleanup_sessions_periodically(interval_seconds: int) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            async for db in get_db():
                deleted = await cleanup_expired_sessions(db)
                await db.commit()
                if deleted:
                    logger.info("expired_sessions_cleaned", extra={"deleted_count": deleted})
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("expired_session_cleanup_failed")


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
    cleanup_task = asyncio.create_task(cleanup_sessions_periodically(config.session_cleanup_interval_seconds))
    try:
        yield
    finally:
        cleanup_task.cancel()
        await asyncio.gather(cleanup_task, return_exceptions=True)
        await dispose_database()
        logger.info("backend_stopped")
