import unittest

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import AppConfig
from app.db.connection import create_database_engine


class DatabaseConnectionTests(unittest.TestCase):
    def test_create_database_engine_uses_configured_url(self) -> None:
        config = AppConfig(
            app_env="test",
            database_url="postgresql+asyncpg://user:pass@localhost:5432/omgm",
        )

        engine = create_database_engine(config)

        self.assertIsInstance(engine, AsyncEngine)
        self.assertIn("localhost", str(engine.url))
