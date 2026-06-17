from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db.password_reset import queries
from tests.db.sqlalchemy_fakes import build_connection


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.password_reset.queries.get_database", return_value=pool)


async def test_create_reset_token_executes_insert() -> None:
    connection = build_connection()
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    with mock_pool(connection):
        await queries.create_reset_token(str(uuid4()), "token-hash", expires_at)

    connection.execute.assert_awaited_once()


async def test_get_valid_reset_token_returns_row_dict() -> None:
    row = {"id": uuid4(), "user_id": uuid4()}
    connection = build_connection(row)

    with mock_pool(connection):
        result = await queries.get_valid_reset_token("token-hash")

    assert result == row
    connection.execute.assert_awaited_once()


async def test_get_valid_reset_token_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        result = await queries.get_valid_reset_token("token-hash")

    assert result is None
    connection.execute.assert_awaited_once()


async def test_mark_token_used_executes_update() -> None:
    connection = build_connection()

    with mock_pool(connection):
        await queries.mark_token_used(str(uuid4()))

    connection.execute.assert_awaited_once()
