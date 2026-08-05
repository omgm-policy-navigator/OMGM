import os
import unittest
from unittest.mock import patch

from app.core.config import AppConfig
from app.core.errors import ConfigurationError

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/test_db"


class ConfigTests(unittest.TestCase):
    def test_required_env_loads(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL}, clear=True):
            config = AppConfig.from_env()

        self.assertEqual(config.app_env, "local")
        self.assertEqual(config.backend_host, "0.0.0.0")
        self.assertEqual(config.backend_port, 8000)
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.database_url, TEST_DATABASE_URL)
        self.assertEqual(config.database_pool_size, 5)
        self.assertEqual(config.database_max_overflow, 10)

    def test_missing_database_url_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_invalid_port_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL, "BACKEND_PORT": "not-a-number"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_invalid_log_level_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL, "LOG_LEVEL": "TRACE"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_invalid_pool_size_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL, "DATABASE_POOL_SIZE": "0"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()
