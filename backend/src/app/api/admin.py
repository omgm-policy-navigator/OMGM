from __future__ import annotations

import secrets
from http import HTTPStatus

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.errors import AppError
from app.db.session import get_db
from app.modules.sessions.service import cleanup_expired_sessions

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
DB_DEPENDENCY = Depends(get_db)


class CleanupResponse(BaseModel):
    deleted_sessions: int = Field(alias="deletedSessions")


def require_admin(request: Request, authorization: str | None = Header(default=None)) -> None:
    config: AppConfig = request.app.state.config
    if not config.admin_api_key:
        raise AppError("ADMIN_API_DISABLED", "Admin API is not configured.", HTTPStatus.SERVICE_UNAVAILABLE)
    scheme, _, credential = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(credential, config.admin_api_key):
        raise AppError("ADMIN_UNAUTHORIZED", "Admin authentication is required.", HTTPStatus.UNAUTHORIZED)


@router.post("/sessions/cleanup", response_model=CleanupResponse, dependencies=[Depends(require_admin)])
async def cleanup_sessions(db: AsyncSession = DB_DEPENDENCY) -> CleanupResponse:
    deleted = await cleanup_expired_sessions(db)
    await db.commit()
    return CleanupResponse(deletedSessions=deleted)
