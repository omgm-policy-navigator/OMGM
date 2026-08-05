from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.core.config import AppConfig
from app.db.session import check_database

router = APIRouter(tags=["health"])


def health_payload(config: AppConfig) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "omgm-backend",
        "environment": config.app_env,
    }


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    return health_payload(request.app.state.config)


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    payload = health_payload(request.app.state.config)
    try:
        await check_database()
    except Exception:
        payload["status"] = "not_ready"
        payload["database"] = "unavailable"
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)

    payload["database"] = "ok"
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)
