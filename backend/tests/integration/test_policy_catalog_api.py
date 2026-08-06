import asyncio
import json
import unittest
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from app.core.config import AppConfig
from app.db.session import get_db
from app.main import create_app

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


class FakeScalarResult:
    def __init__(self, items: list[Any], one: Any | None = None) -> None:
        self.items = items
        self.one = one

    def all(self) -> list[Any]:
        return self.items

    def scalar_one_or_none(self) -> Any | None:
        return self.one

    def scalars(self) -> "FakeScalarResult":
        return self


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
    return status, json.loads(b"".join(body_messages))


def app_with_session(session: AsyncMock):
    app = create_app(AppConfig(app_env="test", database_url=TEST_DATABASE_URL))

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app


def category(code: str, order: int) -> SimpleNamespace:
    return SimpleNamespace(code=code, name=code.title(), description=f"{code} policies", sort_order=order)


def policy(
    policy_id: str,
    active: bool = True,
    status: str = "APPROVED",
    documents: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=policy_id,
        category_code="housing",
        title="Newlywed Rent Deposit Support",
        agency="Seoul Housing Office",
        region="Seoul",
        summary="Rent deposit interest support for newlywed households.",
        application_period="2026-01-01 to 2026-12-31",
        support_type="Interest subsidy",
        status=status,
        is_active=active,
        official_source_url="https://example.go.kr/policies/housing-001",
        source_label="Official notice",
        reviewed_at=date(2026, 8, 1),
        documents=documents or [],
        rules=[],
    )


def document(policy_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"doc_{policy_id}",
        policy_id=policy_id,
        title="Official Source Document",
        url="https://example.go.kr/policies/housing-001",
        document_type="official_notice",
        official_source="Official notice",
        reviewed_at=date(2026, 8, 1),
        collected_at=datetime(2026, 8, 5, tzinfo=UTC),
        document_hash="sha256:policy_housing_001",
        approval_status="APPROVED",
    )


class PolicyCatalogApiTests(unittest.TestCase):
    def test_categories_returns_five_seed_categories(self) -> None:
        session = AsyncMock()
        session.execute.return_value = FakeScalarResult(
            [
                category("housing", 10),
                category("loan", 20),
                category("cash", 30),
                category("childcare", 40),
                category("education", 50),
            ]
        )
        app = app_with_session(session)

        status, body = asyncio.run(asgi_get(app, "/api/categories"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(len(body), 5)
        self.assertEqual(body[0]["code"], "housing")

    def test_category_policies_exposes_only_approved_active_policies(self) -> None:
        session = AsyncMock()
        session.execute.return_value = FakeScalarResult([policy("policy_housing_001")])
        app = app_with_session(session)

        status, body = asyncio.run(asgi_get(app, "/api/categories/housing/policies"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["policyId"], "policy_housing_001")
        self.assertEqual(body[0]["status"], "APPROVED")
        statement = str(session.execute.await_args.args[0])
        self.assertIn("policy.status", statement)
        self.assertIn("policy.is_active", statement)

    def test_policy_detail_returns_agency_source_and_application_period(self) -> None:
        session = AsyncMock()
        session.execute.return_value = FakeScalarResult([], one=policy("policy_housing_001"))
        app = app_with_session(session)

        status, body = asyncio.run(asgi_get(app, "/api/policies/policy_housing_001"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body["agency"], "Seoul Housing Office")
        self.assertEqual(body["applicationPeriod"], "2026-01-01 to 2026-12-31")
        self.assertEqual(body["source"]["url"], "https://example.go.kr/policies/housing-001")
        self.assertEqual(body["source"]["reviewedAt"], "2026-08-01")

    def test_policy_documents_return_official_source_and_reviewed_date(self) -> None:
        session = AsyncMock()
        catalog_document = document("policy_housing_001")
        session.execute.return_value = FakeScalarResult(
            [],
            one=policy("policy_housing_001", documents=[catalog_document]),
        )
        app = app_with_session(session)

        status, body = asyncio.run(asgi_get(app, "/api/policies/policy_housing_001/documents"))

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(body[0]["officialSource"], "Official notice")
        self.assertEqual(body[0]["reviewedAt"], "2026-08-01")
        self.assertEqual(body[0]["documentHash"], "sha256:policy_housing_001")

    def test_missing_or_inactive_policy_returns_404(self) -> None:
        session = AsyncMock()
        session.execute.return_value = FakeScalarResult([], one=None)
        app = app_with_session(session)

        status, body = asyncio.run(asgi_get(app, "/api/policies/policy_inactive_001"))

        self.assertEqual(status, HTTPStatus.NOT_FOUND)
        self.assertEqual(body["error"]["code"], "POLICY_NOT_FOUND")
