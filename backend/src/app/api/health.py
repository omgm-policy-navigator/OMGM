from fastapi import APIRouter, Request

from app.core.config import AppConfig

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
