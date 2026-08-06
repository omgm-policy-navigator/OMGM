from __future__ import annotations

import re
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from ipaddress import ip_address

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class OperationsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, rate_requests: int, rate_window_seconds: int, trusted_proxies: set[str]) -> None:
        super().__init__(app)
        self.rate_requests = rate_requests
        self.rate_window_seconds = rate_window_seconds
        self.trusted_proxies = trusted_proxies
        self._requests: dict[str, deque[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid.uuid4())
        started = time.monotonic()
        identity = self._client_ip(request)
        now = time.monotonic()
        bucket = self._requests.get(identity)
        if bucket is not None:
            while bucket and bucket[0] <= now - self.rate_window_seconds:
                bucket.popleft()
            if not bucket:
                self._requests.pop(identity, None)
                bucket = None
        if bucket is None:
            bucket = deque()
            self._requests[identity] = bucket
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

    def _client_ip(self, request: Request) -> str:
        direct_ip = request.client.host if request.client else "unknown"
        if direct_ip not in self.trusted_proxies:
            return direct_ip
        forwarded = request.headers.get("x-forwarded-for", "").split(",", maxsplit=1)[0].strip()
        try:
            return str(ip_address(forwarded)) if forwarded else direct_ip
        except ValueError:
            return direct_ip

    @staticmethod
    def _error(status: int, code: str, message: str, request_id: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={"error": {"code": code, "message": message}},
            headers={"X-Request-ID": request_id},
        )
