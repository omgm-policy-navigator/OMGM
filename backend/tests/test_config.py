import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.core.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_defaults_load_without_env_file(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig.from_env()

        self.assertEqual(config.app_env, "local")
        self.assertEqual(config.backend_host, "0.0.0.0")
        self.assertEqual(config.backend_port, 8000)
        self.assertEqual(config.log_level, "INFO")

    def test_invalid_port_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"BACKEND_PORT": "not-a-number"}, clear=True):
            with self.assertRaises(ValidationError):
                AppConfig.from_env()

    def test_invalid_log_level_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "TRACE"}, clear=True):
            with self.assertRaises(ValidationError):
                AppConfig.from_env()

    def test_database_url_loads_from_environment(self) -> None:
        database_url = "postgresql+asyncpg://user:pass@localhost:5432/omgm"

        with patch.dict(os.environ, {"DATABASE_URL": database_url}, clear=True):
            config = AppConfig.from_env()

        self.assertEqual(config.sqlalchemy_database_url, database_url)
