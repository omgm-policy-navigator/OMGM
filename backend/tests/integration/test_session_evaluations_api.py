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

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


async def asgi_request(app, method: str, path: str, body=None, headers=None):
    messages = []
    payload = json.dumps(body).encode() if body is not None else b""
    header_pairs = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
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


def rule(rule_id, fact_key, operator, value_text, required=True):
    return SimpleNamespace(
        id=rule_id,
        fact_key=fact_key,
        operator=operator,
        value_text=value_text,
        required=required,
        evidence_text=f"Evidence for {fact_key}",
    )


def policy(policy_id="policy_housing_001", application_period="2026-01-01 to 2026-12-31"):
    return SimpleNamespace(
        id=policy_id,
        application_period=application_period,
        rules=[rule("rule_region", "region", "EQ", "Seoul")],
    )


def evaluation(policy_id="policy_housing_001", state="ACTIVE"):
    now = datetime(2026, 8, 6, 10, tzinfo=UTC)
    return SimpleNamespace(
        policy_id=policy_id,
        eligibility_status="LIKELY_ELIGIBLE",
        evaluation_state=state,
        recommendation_score=1010,
        evidence={
            "satisfied": [],
            "unsatisfied": [],
            "needsConfirmation": [],
            "officialConfirmationRequired": [],
        },
        evaluated_at=now,
        updated_at=now,
    )


class SessionEvaluationApiTests(unittest.TestCase):
    def test_create_evaluations_stores_json_evidence_without_exposing_session_id(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[fact("region", "Seoul")]),
        ), patch(
            "app.modules.sessions.api.list_active_policies_for_category",
            new=AsyncMock(return_value=[policy()]),
        ), patch(
            "app.modules.sessions.api.upsert_policy_evaluation",
            new=AsyncMock(return_value=evaluation()),
        ) as upsert:
            status, _headers, body = asyncio.run(asgi_request(app, "POST", "/api/v1/session/evaluations"))

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "evaluated")
        self.assertEqual(body["items"][0]["policyId"], "policy_housing_001")
        self.assertNotIn("sessionId", json.dumps(body))
        self.assertEqual(upsert.await_args.kwargs["session_id"], 7)
        self.assertEqual(upsert.await_args.kwargs["evidence"]["satisfied"][0]["factKey"], "region")

    def test_get_evaluations_returns_session_scoped_results(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_evaluations",
            new=AsyncMock(return_value=[evaluation()]),
        ) as list_evaluations:
            status, _headers, body = asyncio.run(asgi_request(app, "GET", "/api/v1/session/evaluations"))

        self.assertEqual(status, 200)
        self.assertEqual(body[0]["eligibilityStatus"], "LIKELY_ELIGIBLE")
        self.assertEqual(list_evaluations.await_args.args[1], 7)

    def test_get_policy_evaluation_returns_404_for_missing_session_result(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.get_session_policy_evaluation",
            new=AsyncMock(return_value=None),
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "GET", "/api/v1/session/evaluations/policy_housing_001")
            )

        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "EVALUATION_NOT_FOUND")

    def test_answer_change_marks_existing_evaluations_stale(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[]),
        ), patch("app.modules.sessions.api.upsert_session_fact", new=AsyncMock()), patch(
            "app.modules.sessions.api.mark_session_evaluations_stale",
            new=AsyncMock(return_value=1),
        ) as mark_stale:
            status, _headers, body = asyncio.run(
                asgi_request(
                    app,
                    "POST",
                    "/api/v1/session/answers",
                    body={
                        "answers": [
                            {
                                "questionId": "q_housing_region",
                                "factKey": "region",
                                "value": "Seoul",
                                "confirmed": True,
                            }
                        ]
                    },
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "stored")
        mark_stale.assert_awaited_once_with(db, 7)