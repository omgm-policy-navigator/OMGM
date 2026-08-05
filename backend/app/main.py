from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import AppConfig
from app.core.errors import AppError
from app.core.lifespan import lifespan


def create_app(config: AppConfig | None = None) -> FastAPI:
    app = FastAPI(
        title="나만 결혼해? Backend",
        lifespan=lifespan,
        docs_url="/",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.include_router(api_router)
    if config is not None:
        app.state.config = config

    @app.exception_handler(AppError)
    async def app_error_handler(_request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code.value,
            content={"error": {"code": exc.code, "message": exc.public_message}},
        )

    return app


app = create_app()


def run() -> None:
    import uvicorn

    config = AppConfig.from_env()
    uvicorn.run("app.main:app", host=config.backend_host, port=config.backend_port, reload=False)
