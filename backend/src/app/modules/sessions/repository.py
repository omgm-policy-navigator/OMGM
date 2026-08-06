from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sessions.models import AnonymousSession, UserFact


async def get_session_by_token_hash(db: AsyncSession, token_hash: str) -> AnonymousSession | None:
    result = await db.execute(select(AnonymousSession).where(AnonymousSession.token_hash == token_hash))
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    token_hash: str,
    now: datetime,
    expires_at: datetime,
    idle_expires_at: datetime,
) -> AnonymousSession:
    session = AnonymousSession(
        token_hash=token_hash,
        last_seen_at=now,
        expires_at=expires_at,
        idle_expires_at=idle_expires_at,
    )
    db.add(session)
    await db.flush()
    return session


async def delete_session(db: AsyncSession, session: AnonymousSession) -> None:
    await db.delete(session)


async def delete_expired_sessions(db: AsyncSession, now: datetime) -> int:
    result = await db.execute(
        delete(AnonymousSession).where(
            (AnonymousSession.expires_at <= now) | (AnonymousSession.idle_expires_at <= now)
        )
    )
    return result.rowcount or 0


async def list_facts(db: AsyncSession, session_id: int) -> list[UserFact]:
    statement = select(UserFact).where(UserFact.session_id == session_id).order_by(UserFact.condition_key)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def upsert_fact(
    db: AsyncSession,
    session_id: int,
    condition_key: str,
    value: Any,
    source: str,
    confirmed: bool,
    note: str | None,
) -> UserFact:
    statement = (
        insert(UserFact)
        .values(
            session_id=session_id,
            condition_key=condition_key,
            value=value,
            source=source,
            confirmed=confirmed,
            note=note,
        )
        .on_conflict_do_update(
            constraint="uq_user_fact_session_condition",
            set_={
                "value": value,
                "source": source,
                "confirmed": confirmed,
                "note": note,
            },
        )
        .returning(UserFact)
    )
    result = await db.execute(statement)
    return result.scalar_one()


async def delete_facts_by_keys(db: AsyncSession, session_id: int, condition_keys: set[str]) -> int:
    if not condition_keys:
        return 0
    result = await db.execute(
        delete(UserFact).where(
            UserFact.session_id == session_id,
            UserFact.condition_key.in_(condition_keys),
        )
    )
    return result.rowcount or 0