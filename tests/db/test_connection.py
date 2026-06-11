from unittest.mock import AsyncMock, MagicMock, patch

from src.db import connection


class FakeConnection:
    def __init__(self) -> None:
        self.execute = AsyncMock(return_value="result")
        self.begin = MagicMock(return_value="transaction")
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


class FakeConnectContext:
    def __init__(self, fake_connection: FakeConnection) -> None:
        self.fake_connection = fake_connection

    async def __aenter__(self):
        return self.fake_connection

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None


class FakeEngine:
    def __init__(self, fake_connection: FakeConnection) -> None:
        self.fake_connection = fake_connection

    def connect(self):
        return FakeConnectContext(self.fake_connection)


async def test_init_database_sets_module_engine() -> None:
    mock_engine = MagicMock()

    with patch("src.db.connection.create_async_engine", return_value=mock_engine):
        await connection.init_database()

    assert connection.get_database().engine is mock_engine


async def test_close_database_disposes_engine() -> None:
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    connection._engine = mock_engine

    await connection.close_database()

    mock_engine.dispose.assert_awaited_once()


async def test_database_connection_delegates_execute_and_transaction() -> None:
    fake_connection = FakeConnection()
    database_connection = connection.DatabaseConnection(fake_connection)

    result = await database_connection.execute("statement", {"id": "value"})

    assert result == "result"
    fake_connection.execute.assert_awaited_once_with("statement", {"id": "value"})
    assert database_connection.transaction() == "transaction"


async def test_database_acquire_commits_successful_connection() -> None:
    fake_connection = FakeConnection()
    database = connection.Database(FakeEngine(fake_connection))

    async with database.acquire() as database_connection:
        assert database_connection.connection is fake_connection

    fake_connection.commit.assert_awaited_once()
    fake_connection.rollback.assert_not_awaited()


async def test_database_acquire_rolls_back_failed_connection() -> None:
    fake_connection = FakeConnection()
    database = connection.Database(FakeEngine(fake_connection))

    try:
        async with database.acquire():
            raise RuntimeError("failure")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError")

    fake_connection.rollback.assert_awaited_once()
    fake_connection.commit.assert_not_awaited()
