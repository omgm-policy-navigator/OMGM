import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import AppConfig
from app.core.errors import AppError
from app.db.session import get_db
from app.main import create_app
from app.modules.sessions.models import AnonymousSession, UserFact
from app.modules.sessions.security import generate_session_token
from app.modules.sessions.service import cleanup_expired_sessions, require_session

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


class FakeScalarResult:
    def __init__(self, one=None, items=None) -> None:
        self.one = one
        self.items = items or []

    def scalar_one_or_none(self):
        return self.one

    def scalar_one(self):
        return self.one

    def scalars(self):
        return self

    def all(self):
        return self.items


async def asgi_request(app, method: str, path: str, body=None, headers=None):
    messages = []
    payload = json.dumps(body).encode() if body is not None else b""
    header_pairs = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    if body is not None and "content-type" not in {k.lower() for k in (headers or {})}:
        header_pairs.append((b"content-type", b"application/json"))

    async def receive():
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message):
        messages.append(message)

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
            "headers": header_pairs,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    start = next(message for message in messages if message["type"] == "http.response.start")
    body_bytes = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    parsed = json.loads(body_bytes) if body_bytes else None
    return start["status"], {k.decode(): v.decode() for k, v in start.get("headers", [])}, parsed


def app_with_session(session):
    app = create_app(AppConfig(app_env="test", database_url=TEST_DATABASE_URL))

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app


class AnonymousSessionApiTests(unittest.TestCase):
    def test_create_session_sets_httponly_cookie_without_json_session_id(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        session = SimpleNamespace(
            expires_at=datetime(2026, 8, 7, tzinfo=UTC),
            idle_expires_at=datetime(2026, 8, 6, 11, tzinfo=UTC),
        )
        result = SimpleNamespace(session=session, token="server-generated-token", created=True)

        with patch("app.modules.sessions.api.cleanup_expired_sessions", new=AsyncMock(return_value=0)), patch(
            "app.modules.sessions.api.create_or_get_session", new=AsyncMock(return_value=result)
        ):
            status, headers, body = asyncio.run(asgi_request(app, "POST", "/api/v1/session"))

        self.assertEqual(status, 201)
        self.assertEqual(body, {"status": "session_created"})
        self.assertNotIn("sessionId", body)
        self.assertNotIn("expiresAt", body)
        cookie = headers["set-cookie"]
        self.assertIn("anonymous_session=server-generated-token", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=lax", cookie)

    def test_client_supplied_json_session_id_is_rejected(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        mocked_create = AsyncMock()

        with patch("app.modules.sessions.api.cleanup_expired_sessions", new=AsyncMock(return_value=0)), patch(
            "app.modules.sessions.api.create_or_get_session", new=mocked_create
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/v1/session", body={"sessionId": "attacker-choice"})
            )

        self.assertEqual(status, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        mocked_create.assert_not_awaited()

    def test_client_supplied_session_header_is_rejected(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        mocked_create = AsyncMock()

        with patch("app.modules.sessions.api.cleanup_expired_sessions", new=AsyncMock(return_value=0)), patch(
            "app.modules.sessions.api.create_or_get_session", new=mocked_create
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/v1/session", headers={"x-session-id": "attacker-choice"})
            )

        self.assertEqual(status, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
        mocked_create.assert_not_awaited()

    def test_delete_session_clears_cookie(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)

        with patch("app.modules.sessions.api.delete_current_session", new=AsyncMock(return_value=True)):
            status, headers, body = asyncio.run(
                asgi_request(app, "DELETE", "/api/v1/session", headers={"cookie": "anonymous_session=abc"})
            )

        self.assertEqual(status, 204)
        self.assertIsNone(body)
        self.assertIn("anonymous_session=", headers["set-cookie"])
        self.assertIn("Max-Age=0", headers["set-cookie"])


class AnonymousSessionServiceTests(unittest.TestCase):
    def test_expired_session_is_rejected(self) -> None:
        db = AsyncMock()
        config = AppConfig(app_env="test", database_url=TEST_DATABASE_URL)
        now = datetime(2026, 8, 6, 10, tzinfo=UTC)
        expired = SimpleNamespace(expires_at=now - timedelta(seconds=1), idle_expires_at=now + timedelta(minutes=1))
        with patch("app.modules.sessions.repository.get_session_by_token_hash", new=AsyncMock(return_value=expired)):
            with self.assertRaises(AppError) as context:
                asyncio.run(require_session(db, config, "token", now=now))

        self.assertEqual(context.exception.code, "SESSION_NOT_FOUND")

    def test_active_session_refreshes_inactivity_timeout(self) -> None:
        db = AsyncMock()
        config = AppConfig(app_env="test", database_url=TEST_DATABASE_URL)
        now = datetime(2026, 8, 6, 10, tzinfo=UTC)
        session = SimpleNamespace(expires_at=now + timedelta(hours=20), idle_expires_at=now + timedelta(minutes=1))
        with patch("app.modules.sessions.repository.get_session_by_token_hash", new=AsyncMock(return_value=session)):
            resolved = asyncio.run(require_session(db, config, "token", now=now))

        self.assertIs(resolved, session)
        self.assertEqual(session.last_seen_at, now)
        self.assertEqual(session.idle_expires_at, now + timedelta(minutes=60))

    def test_cleanup_expired_sessions_delegates_expiry_delete(self) -> None:
        db = AsyncMock()
        now = datetime(2026, 8, 6, 10, tzinfo=UTC)
        with patch("app.modules.sessions.repository.delete_expired_sessions", new=AsyncMock(return_value=3)) as mocked:
            deleted = asyncio.run(cleanup_expired_sessions(db, now=now))

        self.assertEqual(deleted, 3)
        mocked.assert_awaited_once_with(db, now)

    def test_facts_are_scoped_by_session_id(self) -> None:
        db = AsyncMock()
        db.execute.return_value = FakeScalarResult(items=[])
        from app.modules.sessions.repository import list_facts

        asyncio.run(list_facts(db, session_id=42))

        statement = str(db.execute.await_args.args[0])
        self.assertIn("user_fact.session_id", statement)

    def test_user_fact_relationship_cascades_with_session(self) -> None:
        foreign_key = next(iter(UserFact.__table__.foreign_keys))
        self.assertEqual(foreign_key.ondelete, "CASCADE")
        relationship = AnonymousSession.__mapper__.relationships["facts"]
        self.assertIn("delete-orphan", relationship.cascade)


class SessionTokenTests(unittest.TestCase):
    def test_generated_session_token_is_uuid4(self) -> None:
        token = generate_session_token()
        self.assertEqual(len(token), 36)
        self.assertEqual(token[14], "4")
