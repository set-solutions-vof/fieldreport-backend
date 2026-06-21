from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db.auth import queries
from tests.db.sqlalchemy_fakes import build_connection


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.auth.queries.get_database", return_value=pool)


async def test_get_user_by_email_returns_authenticated_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "Demo Company",
        "email": "admin.user@example.com",
        "password_hash": "hash",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
    }
    connection = build_connection(row)

    with mock_pool(connection):
        user = await queries.get_user_by_email("admin.user@example.com")

    assert user is not None
    assert user.email == "admin.user@example.com"
    assert user.password_hash == "hash"
    connection.execute.assert_awaited_once()


async def test_get_user_by_email_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        user = await queries.get_user_by_email("missing@example.com")

    assert user is None
    connection.execute.assert_awaited_once()


async def test_get_user_by_id_returns_current_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "Demo Company",
        "email": "inspector.user@example.com",
        "first_name": "Inspector",
        "last_name": "User",
        "role": "inspector",
    }
    connection = build_connection(row)

    with mock_pool(connection):
        user = await queries.get_user_by_id(str(uuid4()))

    assert user is not None
    assert user.email == "inspector.user@example.com"
    assert user.company_name == "Demo Company"
    connection.execute.assert_awaited_once()


async def test_get_user_by_id_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        user = await queries.get_user_by_id(str(uuid4()))

    assert user is None
    connection.execute.assert_awaited_once()
