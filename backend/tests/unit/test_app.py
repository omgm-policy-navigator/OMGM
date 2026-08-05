import json
import unittest
from http import HTTPStatus

from app.api.health import health_payload
from app.core.config import AppConfig
from app.core.errors import AppError
from app.main import create_app, error_payload


class AppTests(unittest.TestCase):
    def test_health_payload(self) -> None:
        payload = health_payload(AppConfig(app_env="test", database_url="postgresql+asyncpg://user:pass@localhost:5432/test_db"))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service"], "omgm-backend")
        self.assertEqual(payload["environment"], "test")

    def test_fastapi_app_loads(self) -> None:
        app = create_app(AppConfig(app_env="test", database_url="postgresql+asyncpg://user:pass@localhost:5432/test_db"))

        self.assertEqual(app.title, "나만 결혼해? Backend")

    def test_app_error_exposes_safe_fields(self) -> None:
        error = AppError("NOT_FOUND", "Requested resource was not found.", HTTPStatus.NOT_FOUND)

        self.assertEqual(error.code, "NOT_FOUND")
        self.assertEqual(error.public_message, "Requested resource was not found.")

    def test_error_payload_serializes_to_json(self) -> None:
        error = AppError("X", "safe message", HTTPStatus.BAD_REQUEST)
        body = json.dumps(error_payload(error.code, error.public_message))

        self.assertIn("safe message", body)
