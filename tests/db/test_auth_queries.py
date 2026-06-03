from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db import auth_queries


def build_connection(row: dict[str, object] | None) -> SimpleNamespace:
    return SimpleNamespace(
        fetchrow=AsyncMock(return_value=row),
    )


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.auth_queries.get_pool", return_value=pool)


async def test_get_user_by_email_returns_authenticated_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "Demo Company",
        "email": "admin.user@example.com",
        "password_hash": "hash",
        "name": "Admin User",
        "role": "admin",
    }
    connection = build_connection(row)

    with mock_pool(connection):
        user = await auth_queries.get_user_by_email("admin.user@example.com")

    assert user is not None
    assert user.email == "admin.user@example.com"
    assert user.password_hash == "hash"
    connection.fetchrow.assert_awaited_once()


async def test_get_user_by_email_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        user = await auth_queries.get_user_by_email("missing@example.com")

    assert user is None
    connection.fetchrow.assert_awaited_once()


async def test_get_user_by_id_returns_current_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "Demo Company",
        "email": "inspector.user@example.com",
        "name": "Inspector User",
        "role": "inspector",
    }
    connection = build_connection(row)

    with mock_pool(connection):
        user = await auth_queries.get_user_by_id(str(uuid4()))

    assert user is not None
    assert user.email == "inspector.user@example.com"
    assert user.company_name == "Demo Company"
    connection.fetchrow.assert_awaited_once()


async def test_get_user_by_id_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        user = await auth_queries.get_user_by_id(str(uuid4()))

    assert user is None
    connection.fetchrow.assert_awaited_once()
