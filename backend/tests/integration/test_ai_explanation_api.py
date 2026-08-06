import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import AppConfig
from app.db.session import get_db
from app.llm import AIOutput, FakeLLMProvider
from app.main import create_app
from app.modules.ai.api import rag_query_for_bundle
from app.modules.ai.schemas import CitationResponse

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


async def asgi_request(app, method: str, path: str, query_string: bytes = b"", body=None, headers=None):
    messages = []
    payload = json.dumps(body).encode() if body is not None else b""
    header_pairs = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    if body is not None and "content-type" not in {key.lower() for key in (headers or {})}:
        header_pairs.append((b"content-type", b"application/json"))

    receive_count = 0

    async def receive():
        nonlocal receive_count
        receive_count += 1
        if receive_count > 1:
            return {"type": "http.disconnect"}
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
    response_headers = {key.decode(): value.decode() for key, value in start.get("headers", [])}
    content_type = response_headers.get("content-type", "")
    parsed = body_bytes.decode() if content_type.startswith("text/event-stream") else json.loads(body_bytes)
    return start["status"], response_headers, parsed


def app_with_session(session):
    app = create_app(AppConfig(app_env="test", database_url=TEST_DATABASE_URL))

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.llm_provider = FakeLLMProvider(
        output=AIOutput(
            answer=(
                '{"summary":"Generated explanation from official evidence.",'
                '"reasons":["The explanation follows stored rule evidence."],'
                '"next_steps":["Review the official citation."],'
                '"disclaimer":"Official confirmation may still be required."}'
            ),
            resultStatus="ANSWERED",
            citations=[
                {
                    "sourceId": "doc_ignored",
                    "title": "Ignored",
                    "url": "https://example.go.kr/ignored",
                    "policyVersionId": "policy_housing_001",
                    "evidenceId": "ignored",
                }
            ],
        )
    )
    return app


def active_session():
    now = datetime(2026, 8, 6, 10, tzinfo=UTC)
    return SimpleNamespace(
        id=7,
        selected_category_code="housing",
        expires_at=now + timedelta(hours=20),
        idle_expires_at=now + timedelta(minutes=60),
    )


def policy_bundle():
    policy = SimpleNamespace(
        id="policy_housing_001",
        title="Housing support",
        summary="Rent support",
        application_period="2026-01-01 to 2026-12-31",
        category_code="housing",
        support_type="rent",
    )
    evaluation = SimpleNamespace(
        policy_id="policy_housing_001",
        eligibility_status="LIKELY_ELIGIBLE",
        evaluation_state="ACTIVE",
        evidence={
            "satisfied": [{"factKey": "region"}],
            "unsatisfied": [],
            "needsConfirmation": [{"factKey": "income"}],
            "officialConfirmationRequired": [],
        },
    )
    document = SimpleNamespace(
        id="doc_1",
        policy_id="policy_housing_001",
        title="Official notice",
        url="https://example.go.kr/policy/1",
        official_source="Example Office",
        document_hash="hash_1",
    )
    return SimpleNamespace(policy=policy, evaluation=evaluation, documents=(document,))


def rag_citations():
    return (
        CitationResponse(
            sourceId="doc_chunk_1",
            policyId="policy_housing_001",
            title="Official notice chunk",
            url="https://example.go.kr/policy/1",
            sourceLabel="OFFICIAL",
            evidenceId="chunk_1",
            excerpt="Official evidence.",
            sourceLocation="heading:eligibility",
            similarity=0.88,
        ),
    )


class AIExplanationApiTests(unittest.TestCase):
    def test_explain_policy_uses_cookie_session_and_rag_citations(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.ai.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.ai.api.get_policy_evidence_bundle",
            new=AsyncMock(return_value=policy_bundle()),
        ) as get_bundle, patch(
            "app.modules.ai.api.retrieve_rag_citations",
            new=AsyncMock(return_value=rag_citations()),
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/policies/policy_housing_001/explain", body={"question": "Explain"})
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["policyId"], "policy_housing_001")
        self.assertEqual(body["eligibilityStatus"], "LIKELY_ELIGIBLE")
        self.assertEqual(body["citations"][0]["sourceId"], "doc_chunk_1")
        self.assertNotIn("sessionId", json.dumps(body))
        get_bundle.assert_awaited_once_with(db, session_id=7, policy_id="policy_housing_001")

    def test_no_rag_citations_requires_official_confirmation(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.ai.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.ai.api.get_policy_evidence_bundle",
            new=AsyncMock(return_value=policy_bundle()),
        ), patch(
            "app.modules.ai.api.retrieve_rag_citations",
            new=AsyncMock(return_value=()),
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/policies/policy_housing_001/explain", body={"question": "Explain"})
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["eligibilityStatus"], "LIKELY_ELIGIBLE")
        self.assertEqual(body["aiStatus"], "FALLBACK")
        self.assertEqual(body["citations"][0]["url"], "https://example.go.kr/policy/1")
        self.assertIn("Housing support", body["answer"])

    def test_chat_without_policy_uses_top_session_evaluation(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.ai.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.ai.api.find_policy_evidence_bundle_for_message",
            new=AsyncMock(return_value=None),
        ), patch(
            "app.modules.ai.api.get_top_session_policy_evidence_bundle",
            new=AsyncMock(return_value=policy_bundle()),
        ) as top_bundle, patch(
            "app.modules.ai.api.retrieve_rag_citations",
            new=AsyncMock(return_value=rag_citations()),
        ):
            status, _headers, body = asyncio.run(asgi_request(app, "POST", "/api/chat", body={"message": "Tell me"}))

        self.assertEqual(status, 200)
        self.assertEqual(body["aiStatus"], "GENERATED")
        top_bundle.assert_awaited_once_with(db, session_id=7)

    def test_chat_without_policy_matches_catalog_policy_before_top_evaluation(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.ai.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.ai.api.find_policy_evidence_bundle_for_message",
            new=AsyncMock(return_value=policy_bundle()),
        ) as finder, patch(
            "app.modules.ai.api.get_top_session_policy_evidence_bundle",
            new=AsyncMock(),
        ) as top_bundle, patch(
            "app.modules.ai.api.retrieve_rag_citations",
            new=AsyncMock(return_value=()),
        ):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/chat", body={"message": "Housing support 알려줘"})
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["aiStatus"], "FALLBACK")
        self.assertEqual(body["policyId"], "policy_housing_001")
        finder.assert_awaited_once_with(db, session_id=7, category_code="housing", message="Housing support 알려줘")
        top_bundle.assert_not_awaited()

    def test_chat_stream_returns_sse_events(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.ai.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.ai.api.get_policy_evidence_bundle",
            new=AsyncMock(return_value=policy_bundle()),
        ), patch(
            "app.modules.ai.api.retrieve_rag_citations",
            new=AsyncMock(return_value=rag_citations()),
        ):
            status, headers, body = asyncio.run(
                asgi_request(
                    app,
                    "GET",
                    "/api/chat/stream",
                    query_string=b"message=Explain&policy_id=policy_housing_001",
                )
            )

        self.assertEqual(status, 200)
        self.assertTrue(headers["content-type"].startswith("text/event-stream"))
        self.assertIn("event: done", body)
        self.assertIn("Generated explanation", body)

    def test_rag_query_excludes_user_pii_and_uses_condition_keys(self) -> None:
        query = rag_query_for_bundle(policy_bundle())

        self.assertIn("Housing support", query)
        self.assertIn("income", query)
        self.assertNotIn("5230", query)
        self.assertNotIn("Seocho", query)
