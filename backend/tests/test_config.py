import os
import unittest
from unittest.mock import patch

from app.core.config import AppConfig
from app.core.errors import ConfigurationError


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
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()

    def test_invalid_log_level_raises_configuration_error(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "TRACE"}, clear=True):
            with self.assertRaises(ConfigurationError):
                AppConfig.from_env()
