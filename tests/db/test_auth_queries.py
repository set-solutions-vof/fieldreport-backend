from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import auth_queries


class FakeConnection:
    def __init__(self, row):
        self.row = row
        self.fetchrow = AsyncMock(return_value=row)
        self.close = AsyncMock()


async def test_get_user_by_email_returns_authenticated_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "LEKK BV",
        "email": "sanne.devries@lekk.nl",
        "password_hash": "hash",
        "name": "Sanne de Vries",
        "role": "admin",
    }
    connection = FakeConnection(row)

    with patch("src.db.auth_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        user = await auth_queries.get_user_by_email("sanne.devries@lekk.nl")

    assert user is not None
    assert user.email == "sanne.devries@lekk.nl"
    assert user.password_hash == "hash"
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_user_by_email_returns_none_when_missing() -> None:
    connection = FakeConnection(None)

    with patch("src.db.auth_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        user = await auth_queries.get_user_by_email("missing@lekk.nl")

    assert user is None
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_user_by_id_returns_current_user() -> None:
    row = {
        "id": uuid4(),
        "company_id": uuid4(),
        "company_name": "LEKK BV",
        "email": "jeroen.vandijk@lekk.nl",
        "name": "Jeroen van Dijk",
        "role": "inspector",
    }
    connection = FakeConnection(row)

    with patch("src.db.auth_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        user = await auth_queries.get_user_by_id(str(uuid4()))

    assert user is not None
    assert user.email == "jeroen.vandijk@lekk.nl"
    assert user.company_name == "LEKK BV"
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_user_by_id_returns_none_when_missing() -> None:
    connection = FakeConnection(None)

    with patch("src.db.auth_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        user = await auth_queries.get_user_by_id(str(uuid4()))

    assert user is None
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()
