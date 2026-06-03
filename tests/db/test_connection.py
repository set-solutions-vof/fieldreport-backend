from unittest.mock import AsyncMock, MagicMock, patch

from src.db import connection


async def test_create_pool_sets_module_pool() -> None:
    mock_pool = MagicMock()

    with patch("src.db.connection.asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        await connection.create_pool()

    assert connection.get_pool() is mock_pool


async def test_close_pool_closes_pool() -> None:
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    connection._pool = mock_pool

    await connection.close_pool()

    mock_pool.close.assert_awaited_once()
