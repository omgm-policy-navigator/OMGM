from __future__ import annotations

from http import HTTPStatus

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.sessions.schemas import CreateSessionResponse, SessionResponse, UpsertUserFactRequest, UserFactResponse
from app.modules.sessions.security import validate_unsafe_origin
from app.modules.sessions.service import (
    cleanup_expired_sessions,
    create_or_get_session,
    delete_current_session,
    list_session_facts,
    require_session,
    upsert_session_fact,
)

router = APIRouter(prefix="/api/v1/session", tags=["session"])

FORBIDDEN_SESSION_INPUTS = {"session_id", "sessionId", "anonymous_session", "x-session-id"}


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


DB_DEPENDENCY = Depends(get_db)
CONFIG_DEPENDENCY = Depends(get_config)


def cookie_secure(config: AppConfig) -> bool:
    return config.app_env.lower() != "local"


def allowed_origins(config: AppConfig) -> list[str]:
    return [origin.strip() for origin in config.cors_allowed_origins.split(",")]


def set_session_cookie(response: Response, config: AppConfig, token: str) -> None:
    response.set_cookie(
        key=config.anonymous_session_cookie_name,
        value=token,
        max_age=config.anonymous_session_absolute_ttl_minutes * 60,
        httponly=True,
        secure=cookie_secure(config),
        samesite=config.anonymous_session_cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response, config: AppConfig) -> None:
    response.delete_cookie(
        key=config.anonymous_session_cookie_name,
        httponly=True,
        secure=cookie_secure(config),
        samesite=config.anonymous_session_cookie_samesite,
        path="/",
    )


def reject_session_identifier() -> None:
    raise AppError(
        "VALIDATION_ERROR",
        "Session identifiers must be sent only by cookie.",
        HTTPStatus.UNPROCESSABLE_ENTITY,
    )


async def reject_client_session_injection(request: Request) -> None:
    if any(name in request.headers for name in ("x-session-id", "x-anonymous-session")):
        reject_session_identifier()
    if not request.headers.get("content-type", "").startswith("application/json"):
        return
    payload = await request.json()
    if isinstance(payload, dict) and FORBIDDEN_SESSION_INPUTS.intersection(payload):
        reject_session_identifier()


@router.post("", response_model=CreateSessionResponse, status_code=HTTPStatus.CREATED)
async def create_session(
    request: Request,
    response: Response,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> CreateSessionResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    await reject_client_session_injection(request)
    await cleanup_expired_sessions(db)
    result = await create_or_get_session(
        db,
        config,
        request.cookies.get(config.anonymous_session_cookie_name),
    )
    await db.commit()
    if result.token is not None:
        set_session_cookie(response, config, result.token)
    if not result.created:
        response.status_code = HTTPStatus.OK
        return CreateSessionResponse(status="session_active")
    return CreateSessionResponse(status="session_created")


@router.get("", response_model=SessionResponse)
async def get_session(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> SessionResponse:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    await db.commit()
    return SessionResponse(expiresAt=session.expires_at, idleExpiresAt=session.idle_expires_at)


@router.delete("", status_code=HTTPStatus.NO_CONTENT)
async def delete_session(
    request: Request,
    response: Response,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> Response:
    validate_unsafe_origin(request, allowed_origins(config))
    await delete_current_session(db, request.cookies.get(config.anonymous_session_cookie_name))
    await db.commit()
    clear_session_cookie(response, config)
    response.status_code = HTTPStatus.NO_CONTENT
    return response


@router.get("/facts", response_model=list[UserFactResponse])
async def get_facts(
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> list[UserFactResponse]:
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    facts = await list_session_facts(db, session)
    await db.commit()
    return [
        UserFactResponse(
            conditionKey=fact.condition_key,
            value=fact.value,
            source=fact.source,
            confirmed=fact.confirmed,
            updatedAt=fact.updated_at,
        )
        for fact in facts
    ]


@router.put("/facts/{condition_key}", response_model=UserFactResponse)
async def put_fact(
    condition_key: str,
    payload: UpsertUserFactRequest,
    request: Request,
    db: AsyncSession = DB_DEPENDENCY,
    config: AppConfig = CONFIG_DEPENDENCY,
) -> UserFactResponse:
    validate_unsafe_origin(request, allowed_origins(config))
    session = await require_session(db, config, request.cookies.get(config.anonymous_session_cookie_name))
    fact = await upsert_session_fact(
        db,
        session,
        condition_key,
        payload.value,
        payload.source,
        payload.confirmed,
        payload.note,
    )
    await db.commit()
    return UserFactResponse(
        conditionKey=fact.condition_key,
        value=fact.value,
        source=fact.source,
        confirmed=fact.confirmed,
        updatedAt=fact.updated_at,
    )
