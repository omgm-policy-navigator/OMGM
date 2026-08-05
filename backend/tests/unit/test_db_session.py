import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.db import session as db_session


class DatabaseSessionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self) -> None:
        db_session._engine = None
        db_session._session_factory = None

    def test_configure_database_uses_pool_settings(self) -> None:
        engine = Mock()

        with patch("app.db.session.create_async_engine", return_value=engine) as create_async_engine:
            db_session.configure_database(
                "postgresql://user:pass@localhost:5432/test_db",
                pool_size=7,
                max_overflow=3,
            )

        create_async_engine.assert_called_once_with(
            "postgresql+asyncpg://user:pass@localhost:5432/test_db",
            pool_pre_ping=True,
            pool_size=7,
            max_overflow=3,
        )

    async def test_get_db_closes_session_after_yield(self) -> None:
        session = AsyncMock()
        db_session._session_factory = Mock(return_value=session)

        generator = db_session.get_db()
        yielded_session = await anext(generator)
        self.assertIs(yielded_session, session)

        with self.assertRaises(StopAsyncIteration):
            await anext(generator)

        session.close.assert_awaited_once()
