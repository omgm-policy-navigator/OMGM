from __future__ import annotations

import re
import uuid

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class RequestBodyLimitMiddleware:
    """Limit actual received bytes, including chunked requests without Content-Length."""

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is None or 0 <= content_length <= self.max_body_bytes:
            body = bytearray()
            more_body = True
            while more_body:
                message = await receive()
                if message["type"] == "http.disconnect":
                    await self.app(scope, self._replay(message), send)
                    return
                chunk = message.get("body", b"")
                body.extend(chunk)
                if len(body) > self.max_body_bytes:
                    await self._reject(scope, receive, send)
                    return
                more_body = bool(message.get("more_body", False))
            replay_message: Message = {"type": "http.request", "body": bytes(body), "more_body": False}
            await self.app(scope, self._replay(replay_message), send)
            return

        await self._reject(scope, receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() != b"content-length":
                continue
            try:
                length = int(value)
            except ValueError:
                return -1
            return length if length >= 0 else -1
        return None

    @staticmethod
    def _replay(message: Message) -> Receive:
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return message

        return replay

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send) -> None:
        supplied_request_id = next(
            (
                value.decode("ascii", errors="ignore")
                for name, value in scope.get("headers", [])
                if name == b"x-request-id"
            ),
            "",
        )
        request_id = supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else str(uuid.uuid4())
        response = JSONResponse(
            status_code=413,
            content={"error": {"code": "REQUEST_TOO_LARGE", "message": "Request body is too large."}},
            headers={"X-Request-ID": request_id},
        )
        await response(scope, receive, send)
