from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    status: str


class SessionResponse(BaseModel):
    status: str = "session_active"
    expires_at: datetime = Field(alias="expiresAt")
    idle_expires_at: datetime = Field(alias="idleExpiresAt")


class UserFactResponse(BaseModel):
    condition_key: str = Field(alias="conditionKey")
    value: Any
    source: str
    confirmed: bool
    updated_at: datetime = Field(alias="updatedAt")


class UpsertUserFactRequest(BaseModel):
    value: Any
    confirmed: bool = True
    source: str = "manual"
    note: str | None = None
