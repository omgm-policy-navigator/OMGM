from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class OperationsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_body_bytes: int, rate_requests: int, rate_window_seconds: int) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.rate_requests = rate_requests
        self.rate_window_seconds = rate_window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid.uuid4())
        started = time.monotonic()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                oversized = int(content_length) > self.max_body_bytes
            except ValueError:
                oversized = True
            if oversized:
                return self._error(413, "REQUEST_TOO_LARGE", "Request body is too large.", request_id)

        identity = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._requests[identity]
        while bucket and bucket[0] <= now - self.rate_window_seconds:
            bucket.popleft()
        if len(bucket) >= self.rate_requests:
            response = self._error(429, "RATE_LIMITED", "Too many requests.", request_id)
            response.headers["Retry-After"] = str(self.rate_window_seconds)
            return response
        bucket.append(now)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "http_request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )
        return response

    @staticmethod
    def _error(status: int, code: str, message: str, request_id: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={"error": {"code": code, "message": message}},
            headers={"X-Request-ID": request_id},
        )
