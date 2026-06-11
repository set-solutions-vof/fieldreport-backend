from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.db.user import queries


class FakeScalarResult:
    def __init__(self, value: str | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> str | None:
        return self.value


def mock_pool(connection: SimpleNamespace):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.user.queries.get_database", return_value=pool)


def build_connection(result: object | None = None) -> SimpleNamespace:
    execute = AsyncMock(return_value=result)

    return SimpleNamespace(execute=execute)


async def test_get_user_password_hash_returns_hash() -> None:
    connection = build_connection(FakeScalarResult("stored-hash"))

    with mock_pool(connection):
        password_hash = await queries.get_user_password_hash(str(uuid4()))

    assert password_hash == "stored-hash"
    connection.execute.assert_awaited_once()


async def test_get_user_password_hash_raises_when_missing() -> None:
    connection = build_connection(FakeScalarResult(None))

    with mock_pool(connection):
        with pytest.raises(RuntimeError):
            await queries.get_user_password_hash(str(uuid4()))

    connection.execute.assert_awaited_once()


async def test_update_user_name_executes_statement() -> None:
    connection = build_connection()

    with mock_pool(connection):
        await queries.update_user_name(str(uuid4()), "Updated Inspector")

    connection.execute.assert_awaited_once()


async def test_update_user_password_executes_statement() -> None:
    connection = build_connection()

    with mock_pool(connection):
        await queries.update_user_password(str(uuid4()), "new-hash")

    connection.execute.assert_awaited_once()
