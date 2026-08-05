import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock

from app.core.config import AppConfig
from app.db.session import get_db
from app.main import create_app

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


async def asgi_get(app, path: str) -> tuple[int, dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )

    status = next(message["status"] for message in messages if message["type"] == "http.response.start")
    body_messages = (message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    response_body = b"".join(body_messages)
    return status, json.loads(response_body)


def make_test_config() -> AppConfig:
    return AppConfig(app_env="test", database_url=TEST_DATABASE_URL)


class HealthApiTests(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        app = create_app(make_test_config())

        status, body = asyncio.run(asgi_get(app, "/health/live"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["service"], "omgm-backend")
        self.assertEqual(body["environment"], "test")

    def test_readiness_returns_ok_when_database_ping_succeeds(self) -> None:
        app = create_app(make_test_config())
        session = AsyncMock()

        async def override_get_db() -> AsyncIterator[AsyncMock]:
            yield session

        app.dependency_overrides[get_db] = override_get_db

        status, body = asyncio.run(asgi_get(app, "/health/ready"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["database"], "connected")
        session.execute.assert_awaited_once()

    def test_readiness_returns_unavailable_when_database_ping_fails(self) -> None:
        app = create_app(make_test_config())
        session = AsyncMock()
        session.execute.side_effect = RuntimeError("db unavailable")

        async def override_get_db() -> AsyncIterator[AsyncMock]:
            yield session

        app.dependency_overrides[get_db] = override_get_db

        status, body = asyncio.run(asgi_get(app, "/health/ready"))

        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(body["status"], "not_ready")
        self.assertEqual(body["database"], "unavailable")

    def test_readiness_returns_unavailable_when_database_ping_times_out(self) -> None:
        app = create_app(make_test_config())
        session = AsyncMock()

        async def slow_execute(_statement: object) -> None:
            await asyncio.sleep(3)

        session.execute.side_effect = slow_execute

        async def override_get_db() -> AsyncIterator[AsyncMock]:
            yield session

        app.dependency_overrides[get_db] = override_get_db

        status, body = asyncio.run(asgi_get(app, "/health/ready"))

        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(body["status"], "not_ready")
        self.assertEqual(body["database"], "unavailable")
