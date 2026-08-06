from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterable
from http import HTTPStatus

from fastapi import Request

from app.core.errors import AppError


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validate_unsafe_origin(request: Request, allowed_origins: Iterable[str]) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = {item.strip().rstrip("/") for item in allowed_origins if item.strip()}
    if origin.rstrip("/") not in allowed:
        raise AppError("SESSION_ORIGIN_FORBIDDEN", "Request origin is not allowed.", status_code=HTTPStatus.FORBIDDEN)
