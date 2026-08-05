import asyncio
import json
import unittest
from http import HTTPStatus
from typing import Any

from fastapi import Body

from app.core.config import AppConfig
from app.main import create_app


async def asgi_request(app, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    body_bytes = json.dumps(body or {}).encode()
    messages: list[dict[str, Any]] = []
    received = False

    async def receive() -> dict[str, Any]:
        nonlocal received
        if received:
            return {"type": "http.disconnect"}
        received = True
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    try:
        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.3"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "root_path": "",
            },
            receive,
            send,
        )
    except Exception:
        if not any(message["type"] == "http.response.start" for message in messages):
            raise

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return status, json.loads(response_body)


class ErrorResponseIntegrationTests(unittest.TestCase):
    def test_request_validation_error_uses_error_envelope(self) -> None:
        app = create_app(AppConfig(app_env="test"))

        @app.post("/validation-test")
        def validation_test(value: int = Body(..., embed=True)) -> dict[str, int]:
            return {"value": value}

        status, body = asyncio.run(asgi_request(app, "POST", "/validation-test", {"value": "not-an-int"}))

        self.assertEqual(status, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(body["error"]["message"], "Request validation failed.")
        self.assertEqual(body["error"]["details"][0]["location"], ["body", "value"])

    def test_unhandled_error_uses_safe_error_envelope(self) -> None:
        app = create_app(AppConfig(app_env="test"))

        @app.get("/internal-error-test")
        def internal_error_test() -> None:
            raise RuntimeError("sensitive internal detail")

        status, body = asyncio.run(asgi_request(app, "GET", "/internal-error-test"))

        self.assertEqual(status, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertEqual(
            body,
            {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}},
        )
