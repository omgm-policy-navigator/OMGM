import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import AppConfig
from app.db.session import get_db
from app.main import create_app
from app.modules.graph.projection import (
    CENTERED_GRAPH_MAX_DEPTH,
    GraphCategory,
    GraphEvaluation,
    GraphPolicy,
    GraphRelation,
)

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


async def asgi_request(app, method: str, path: str, query_string: bytes = b"", body=None, headers=None):
    messages = []
    payload = json.dumps(body).encode() if body is not None else b""
    header_pairs = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    if body is not None and "content-type" not in {key.lower() for key in (headers or {})}:
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
            "query_string": query_string,
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
    return start["status"], {key.decode(): value.decode() for key, value in start.get("headers", [])}, parsed


def app_with_session(session):
    app = create_app(AppConfig(app_env="test", database_url=TEST_DATABASE_URL))

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app


def active_session(category_code="housing"):
    now = datetime(2026, 8, 6, 10, tzinfo=UTC)
    return SimpleNamespace(
        id=7,
        selected_category_code=category_code,
        expires_at=now + timedelta(hours=20),
        idle_expires_at=now + timedelta(minutes=60),
    )


def fact(key, value):
    return SimpleNamespace(condition_key=key, value=value)


class SessionGraphApiTests(unittest.TestCase):
    def test_get_graph_uses_cookie_session_scope_and_selected_category(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[fact("region", "Seoul")]),
        ), patch(
            "app.modules.sessions.api.list_graph_categories",
            new=AsyncMock(return_value=[GraphCategory("housing", "Housing")]),
        ) as categories, patch(
            "app.modules.sessions.api.list_graph_policies",
            new=AsyncMock(return_value=[GraphPolicy("policy_housing_001", "housing", "Rent", "Seoul", "Grant")]),
        ) as policies, patch(
            "app.modules.sessions.api.list_graph_evaluations",
            new=AsyncMock(return_value=[GraphEvaluation("policy_housing_001", "LIKELY_ELIGIBLE", "ACTIVE", 1010, {})]),
        ) as evaluations, patch(
            "app.modules.sessions.api.list_graph_relations",
            new=AsyncMock(return_value=[]),
        ):
            status, _headers, body = asyncio.run(asgi_request(app, "GET", "/api/v1/session/graph"))

        self.assertEqual(status, 200)
        self.assertEqual(body["nodeCount"], len(body["nodes"]))
        self.assertNotIn("sessionId", json.dumps(body))
        categories.assert_awaited_once_with(db, "housing")
        policies.assert_awaited_once_with(db, "housing", None)
        evaluations.assert_awaited_once_with(db, 7, {"policy_housing_001"})

    def test_get_graph_accepts_category_filter_and_policy_center(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.modules.sessions.api.list_centered_graph_policy_ids",
            new=AsyncMock(return_value={"policy_loan_001", "policy_housing_001"}),
        ) as centered_ids, patch(
            "app.modules.sessions.api.list_graph_categories",
            new=AsyncMock(return_value=[GraphCategory("loan", "Loan")]),
        ) as categories, patch(
            "app.modules.sessions.api.list_graph_policies",
            new=AsyncMock(
                return_value=[
                    GraphPolicy("policy_loan_001", "loan", "Loan", "National", "Loan"),
                    GraphPolicy("policy_housing_001", "housing", "Rent", "Seoul", "Grant"),
                ]
            ),
        ) as policies, patch(
            "app.modules.sessions.api.list_graph_evaluations",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.modules.sessions.api.list_graph_relations",
            new=AsyncMock(return_value=[GraphRelation("rel_1", "policy_loan_001", "policy_housing_001", "RELATED")]),
        ):
            status, _headers, body = asyncio.run(
                asgi_request(
                    app,
                    "GET",
                    "/api/v1/session/graph",
                    query_string=b"category=Loan&policy_id=policy_loan_001&max_nodes=20",
                )
            )

        self.assertEqual(status, 200)
        categories.assert_awaited_once_with(db, "loan")
        centered_ids.assert_awaited_once_with(
            db,
            "policy_loan_001",
            max_depth=CENTERED_GRAPH_MAX_DEPTH,
            category_code="loan",
        )
        policies.assert_awaited_once_with(db, None, {"policy_loan_001", "policy_housing_001"})
        self.assertTrue(any(node["id"] == "POLICY:policy_loan_001" for node in body["nodes"]))

    def test_get_graph_rejects_unknown_category(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())):
            status, _headers, body = asyncio.run(
                asgi_request(app, "GET", "/api/v1/session/graph", query_string=b"category=unknown")
            )

        self.assertEqual(status, 422)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")