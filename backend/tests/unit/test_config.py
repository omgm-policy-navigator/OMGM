import os
import unittest
from pathlib import Path
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
        self.assertTrue(config.policy_seed_dir.is_dir())
        self.assertEqual(config.llm_provider, "ollama")
        self.assertEqual(config.ollama_generation_model, "qwen3:4b")
        self.assertEqual(config.llm_temperature, 0.1)
        self.assertEqual(config.llm_timeout_seconds, 30)

    def test_policy_seed_directory_can_be_overridden(self) -> None:
        custom_path = Path("custom-policy-seed")
        with patch.dict(
            os.environ,
            {"DATABASE_URL": TEST_DATABASE_URL, "POLICY_SEED_DIR": str(custom_path)},
            clear=True,
        ):
            config = AppConfig.from_env()

        self.assertEqual(config.policy_seed_dir, custom_path)

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

    def test_invalid_llm_provider_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL, "LLM_PROVIDER": "remote"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_invalid_llm_temperature_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL, "LLM_TEMPERATURE": "3"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()
