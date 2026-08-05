import asyncio

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.logging import get_logger
from app.db.session import get_db

READINESS_TIMEOUT_SECONDS = 2.0
NO_CACHE_HEADERS = {"Cache-Control": "no-cache, no-store, must-revalidate"}

logger = get_logger(__name__)
router = APIRouter(tags=["health"])
DB_SESSION_DEPENDENCY = Depends(get_db)


def health_payload(config: AppConfig) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "omgm-backend",
        "environment": config.app_env,
    }


def readiness_response(status_code: int, payload: dict[str, str]) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=payload, headers=NO_CACHE_HEADERS)


@router.get("/health/live")
def liveness(request: Request) -> dict[str, str]:
    return health_payload(request.app.state.config)


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    return liveness(request)


@router.get("/health/ready")
async def readiness(request: Request, db: AsyncSession = DB_SESSION_DEPENDENCY) -> JSONResponse:
    payload = health_payload(request.app.state.config)
    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=READINESS_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.error("DB readiness check timed out", exc_info=True)
        payload["status"] = "not_ready"
        payload["database"] = "timeout"
        return readiness_response(status.HTTP_503_SERVICE_UNAVAILABLE, payload)
    except Exception:
        logger.error("DB readiness check failed", exc_info=True)
        payload["status"] = "not_ready"
        payload["database"] = "unavailable"
        return readiness_response(status.HTTP_503_SERVICE_UNAVAILABLE, payload)

    payload["status"] = "ready"
    payload["database"] = "connected"
    return readiness_response(status.HTTP_200_OK, payload)


@router.get("/ready")
async def ready(request: Request, db: AsyncSession = DB_SESSION_DEPENDENCY) -> JSONResponse:
    return await readiness(request, db)
