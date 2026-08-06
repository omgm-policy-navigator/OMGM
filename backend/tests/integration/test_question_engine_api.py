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
from app.modules.questions.engine import (
    QuestionTemplate,
    ShowCondition,
    dependent_fact_keys,
    next_questions,
    progress,
    validate_question_dag,
)

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


def fact(key, value, confirmed=True):
    return SimpleNamespace(condition_key=key, value=value, confirmed=confirmed)


class QuestionEngineUnitTests(unittest.TestCase):
    def test_next_questions_prioritize_category_required_unanswered(self) -> None:
        questions = next_questions("housing", {})

        self.assertEqual(questions[0].question_id, "q_housing_region")
        self.assertEqual(questions[0].priority, 10)

    def test_answered_questions_are_excluded(self) -> None:
        questions = next_questions("housing", {"region": "Seoul"})

        self.assertEqual(questions[0].fact_key, "marital_status")

    def test_show_condition_hides_child_question_until_parent_matches(self) -> None:
        base_facts = {"region": "National", "pregnancy_status": "pregnant"}
        without_child = [
            question.fact_key
            for question in next_questions("childcare", {**base_facts, "has_child": False}, limit=5)
        ]
        with_child = [
            question.fact_key
            for question in next_questions("childcare", {**base_facts, "has_child": True}, limit=5)
        ]

        self.assertNotIn("child_age_months", without_child)
        self.assertIn("child_age_months", with_child)

    def test_progress_counts_only_visible_required_questions(self) -> None:
        answered, total, complete = progress(
            "childcare",
            {"region": "National", "pregnancy_status": "pregnant", "has_child": False},
        )

        self.assertEqual(answered, 3)
        self.assertEqual(total, 3)
        self.assertTrue(complete)



    def test_question_graph_rejects_circular_dependency(self) -> None:
        questions = (
            QuestionTemplate(
                "q_a",
                "housing",
                "a",
                "A?",
                "boolean",
                True,
                10,
                10,
                show_condition=ShowCondition("b", True),
            ),
            QuestionTemplate(
                "q_b",
                "housing",
                "b",
                "B?",
                "boolean",
                True,
                20,
                10,
                show_condition=ShowCondition("a", True),
            ),
        )

        with self.assertRaises(ValueError):
            validate_question_dag(questions)

    def test_dependent_fact_keys_traverses_all_descendants(self) -> None:
        questions = (
            QuestionTemplate("q_parent", "housing", "parent", "Parent?", "boolean", True, 10, 10),
            QuestionTemplate(
                "q_child",
                "housing",
                "child",
                "Child?",
                "boolean",
                True,
                20,
                10,
                parent_question_id="q_parent",
                show_condition=ShowCondition("parent", True),
            ),
            QuestionTemplate(
                "q_grandchild",
                "housing",
                "grandchild",
                "Grandchild?",
                "boolean",
                True,
                30,
                10,
                parent_question_id="q_child",
                show_condition=ShowCondition("child", True),
            ),
        )

        self.assertEqual(dependent_fact_keys("housing", "parent", questions), {"child", "grandchild"})

class QuestionEngineApiTests(unittest.TestCase):
    def test_select_category_stores_session_category(self) -> None:
        db = AsyncMock()
        session = active_session(category_code=None)
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=session)):
            status, _headers, body = asyncio.run(
                asgi_request(app, "POST", "/api/v1/session/category", body={"categoryCode": "Housing"})
            )

        self.assertEqual(status, 200)
        self.assertEqual(session.selected_category_code, "housing")
        self.assertEqual(body["categoryCode"], "housing")

    def test_reset_category_session_deletes_only_selected_category_state(self) -> None:
        db = AsyncMock()
        session = active_session("loan")
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=session)), patch(
            "app.modules.sessions.api.delete_session_facts_by_keys",
            new=AsyncMock(return_value=4),
        ) as delete_facts, patch(
            "app.modules.sessions.api.delete_session_evaluations_for_category",
            new=AsyncMock(return_value=2),
        ) as delete_evaluations:
            status, _headers, body = asyncio.run(
                asgi_request(
                    app,
                    "POST",
                    "/api/v1/session/category/reset",
                    body={"categoryCode": "housing"},
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(session.selected_category_code, "housing")
        self.assertEqual(body["status"], "category_session_reset")
        self.assertEqual(body["deletedFacts"], 4)
        self.assertEqual(body["deletedEvaluations"], 2)
        delete_facts.assert_awaited_once()
        self.assertEqual(delete_facts.await_args.args[1], session)
        self.assertEqual(
            delete_facts.await_args.args[2],
            {"region", "marital_status", "household_income_range", "housing_status", "lease_type"},
        )
        delete_evaluations.assert_awaited_once_with(db, session.id, "housing")

    def test_next_question_excludes_existing_facts(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[fact("region", "Seoul")]),
        ):
            status, _headers, body = asyncio.run(asgi_request(app, "GET", "/api/v1/session/questions/next"))

        self.assertEqual(status, 200)
        self.assertEqual(body["items"][0]["factKey"], "marital_status")
        self.assertFalse(body["complete"])

    def test_submit_answers_returns_conflict_reconfirmation_question(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=[fact("region", "Seoul")]),
        ), patch("app.modules.sessions.api.upsert_session_fact", new=AsyncMock()) as upsert:
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
                                "value": "Busan",
                                "confirmed": True,
                            }
                        ]
                    },
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "conflicted")
        self.assertEqual(body["conflicts"][0]["factKey"], "region")
        self.assertEqual(body["conflicts"][0]["question"]["questionId"], "q_housing_region")
        upsert.assert_not_awaited()

    def test_progress_reports_completion(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        facts = [
            fact("region", "Seoul"),
            fact("marital_status", "newlywed"),
            fact("household_income_range", "50m_to_80m"),
            fact("housing_status", "no_home"),
            fact("lease_type", "jeonse"),
        ]
        with patch("app.modules.sessions.api.require_session", new=AsyncMock(return_value=active_session())), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=facts),
        ):
            status, _headers, body = asyncio.run(asgi_request(app, "GET", "/api/v1/session/questions/progress"))

        self.assertEqual(status, 200)
        self.assertEqual(body["answeredRequired"], 5)
        self.assertEqual(body["totalRequired"], 5)
        self.assertTrue(body["complete"])
    def test_changed_parent_answer_invalidates_dependent_child_facts(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        existing = [fact("marriage_registered", True), fact("marriage_registration_date", "2026-01-01")]
        require_session = AsyncMock(return_value=active_session("cash"))
        with patch("app.modules.sessions.api.require_session", new=require_session), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=existing),
        ), patch("app.modules.sessions.api.upsert_session_fact", new=AsyncMock()) as upsert, patch(
            "app.modules.sessions.api.delete_session_facts_by_keys", new=AsyncMock(return_value=1)
        ) as delete_facts:
            status, _headers, body = asyncio.run(
                asgi_request(
                    app,
                    "POST",
                    "/api/v1/session/answers",
                    body={
                        "answers": [
                            {
                                "questionId": "q_cash_marriage_registered",
                                "factKey": "marriage_registered",
                                "value": False,
                                "confirmed": True,
                            }
                        ]
                    },
                )
            )

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "stored")
        upsert.assert_awaited_once()
        delete_facts.assert_awaited_once()
        self.assertEqual(delete_facts.await_args.args[2], {"marriage_registration_date"})
        next_fact_keys = [question["factKey"] for question in body["nextQuestions"]]
        self.assertNotIn("marriage_registration_date", next_fact_keys)
    def test_submit_answer_does_not_commit_when_dependent_invalidation_fails(self) -> None:
        db = AsyncMock()
        app = app_with_session(db)
        existing = [fact("marriage_registered", True), fact("marriage_registration_date", "2026-01-01")]
        with patch(
            "app.modules.sessions.api.require_session",
            new=AsyncMock(return_value=active_session("cash")),
        ), patch(
            "app.modules.sessions.api.list_session_facts",
            new=AsyncMock(return_value=existing),
        ), patch("app.modules.sessions.api.upsert_session_fact", new=AsyncMock()) as upsert, patch(
            "app.modules.sessions.api.delete_session_facts_by_keys",
            new=AsyncMock(side_effect=RuntimeError("delete failed")),
        ):
            with self.assertRaises(RuntimeError):
                asyncio.run(
                    asgi_request(
                        app,
                        "POST",
                        "/api/v1/session/answers",
                        body={
                            "answers": [
                                {
                                    "questionId": "q_cash_marriage_registered",
                                    "factKey": "marriage_registered",
                                    "value": False,
                                    "confirmed": True,
                                }
                            ]
                        },
                    )
                )

        upsert.assert_awaited_once()
        db.commit.assert_not_awaited()
