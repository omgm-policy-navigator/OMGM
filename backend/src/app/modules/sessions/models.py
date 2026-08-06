from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.models import Base


class AnonymousSession(Base):
    __tablename__ = "anonymous_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    facts: Mapped[list[UserFact]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserFact(Base):
    __tablename__ = "user_fact"
    __table_args__ = (
        UniqueConstraint("session_id", "condition_key", name="uq_user_fact_session_condition"),
        Index("ix_user_fact_session_id", "session_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("anonymous_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    condition_key: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    confirmed: Mapped[bool] = mapped_column(default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    note: Mapped[str | None] = mapped_column(Text)

    session: Mapped[AnonymousSession] = relationship(back_populates="facts")
