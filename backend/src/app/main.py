from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import AppConfig
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.lifespan import lifespan

logger = get_logger(__name__)


def error_payload(code: str, message: str, details: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def create_app(config: AppConfig | None = None) -> FastAPI:
    app = FastAPI(title="나만 결혼해? Backend", lifespan=lifespan)
    app.include_router(api_router)
    if config is not None:
        app.state.config = config

    @app.exception_handler(AppError)
    async def app_error_handler(_request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code.value,
            content=error_payload(exc.code, exc.public_message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY.value,
            content=error_payload(
                "VALIDATION_ERROR",
                "Request validation failed.",
                [
                    {
                        "location": list(error["loc"]),
                        "message": error["msg"],
                        "type": error["type"],
                    }
                    for error in exc.errors()
                ],
            ),
        )

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled backend error",
            extra={
                "method": request.method,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            content=error_payload("INTERNAL_ERROR", "An unexpected error occurred."),
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    config = AppConfig.from_env()
    uvicorn.run("app.main:app", host=config.backend_host, port=config.backend_port, reload=False)
