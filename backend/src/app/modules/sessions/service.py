from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AppConfig
from app.core.errors import AppError
from app.modules.sessions import repository
from app.modules.sessions.models import AnonymousSession, UserFact
from app.modules.sessions.security import generate_session_token, hash_session_token


@dataclass(frozen=True)
class SessionWithToken:
    session: AnonymousSession
    token: str | None
    created: bool


def utc_now() -> datetime:
    return datetime.now(UTC)


def _absolute_expires_at(now: datetime, config: AppConfig) -> datetime:
    return now + timedelta(minutes=config.anonymous_session_absolute_ttl_minutes)


def _idle_expires_at(now: datetime, config: AppConfig) -> datetime:
    return now + timedelta(minutes=config.anonymous_session_idle_ttl_minutes)


def is_expired(session: AnonymousSession, now: datetime) -> bool:
    return session.expires_at <= now or session.idle_expires_at <= now


def refresh_session_access(session: AnonymousSession, now: datetime, config: AppConfig) -> None:
    session.last_seen_at = now
    session.idle_expires_at = min(session.expires_at, _idle_expires_at(now, config))


async def create_or_get_session(
    db: AsyncSession,
    config: AppConfig,
    existing_token: str | None,
    now: datetime | None = None,
) -> SessionWithToken:
    current_time = now or utc_now()
    if existing_token:
        existing = await repository.get_session_by_token_hash(db, hash_session_token(existing_token))
        if existing is not None and not is_expired(existing, current_time):
            refresh_session_access(existing, current_time, config)
            return SessionWithToken(existing, None, created=False)

    token = generate_session_token()
    session = await repository.create_session(
        db,
        token_hash=hash_session_token(token),
        now=current_time,
        expires_at=_absolute_expires_at(current_time, config),
        idle_expires_at=_idle_expires_at(current_time, config),
    )
    return SessionWithToken(session, token, created=True)


async def require_session(
    db: AsyncSession,
    config: AppConfig,
    token: str | None,
    now: datetime | None = None,
) -> AnonymousSession:
    if not token:
        raise AppError("SESSION_NOT_FOUND", "Anonymous session was not found.", status_code=HTTPStatus.NOT_FOUND)
    current_time = now or utc_now()
    session = await repository.get_session_by_token_hash(db, hash_session_token(token))
    if session is None or is_expired(session, current_time):
        raise AppError("SESSION_NOT_FOUND", "Anonymous session was not found.", status_code=HTTPStatus.NOT_FOUND)
    refresh_session_access(session, current_time, config)
    return session


async def delete_current_session(db: AsyncSession, token: str | None) -> bool:
    if not token:
        return False
    session = await repository.get_session_by_token_hash(db, hash_session_token(token))
    if session is None:
        return False
    await repository.delete_session(db, session)
    return True


async def list_session_facts(db: AsyncSession, session: AnonymousSession) -> list[UserFact]:
    return await repository.list_facts(db, session.id)


async def upsert_session_fact(
    db: AsyncSession,
    session: AnonymousSession,
    condition_key: str,
    value: Any,
    source: str,
    confirmed: bool,
    note: str | None,
) -> UserFact:
    return await repository.upsert_fact(db, session.id, condition_key, value, source, confirmed, note)


async def cleanup_expired_sessions(db: AsyncSession, now: datetime | None = None) -> int:
    return await repository.delete_expired_sessions(db, now or utc_now())
