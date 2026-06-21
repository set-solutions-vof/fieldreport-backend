from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db.team import queries
from src.models.team.member import TeamMember
from tests.db.sqlalchemy_fakes import build_connection


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.team.queries.get_database", return_value=pool)


async def test_list_company_members_returns_members() -> None:
    member_id = uuid4()
    created_at = datetime.now(UTC)
    row = {
        "id": member_id,
        "first_name": "Admin",
        "last_name": "",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": created_at,
        "last_sign_in_at": None,
    }
    connection = build_connection(rows=[row])

    with mock_pool(connection):
        members = await queries.list_company_members(str(uuid4()))

    assert members == [
        TeamMember(
            id=member_id,
            first_name="Admin",
            last_name="",
            email="admin@example.com",
            role="admin",
            created_at=created_at,
            last_sign_in_at=None,
        )
    ]
    connection.execute.assert_awaited_once()


async def test_get_company_member_returns_member() -> None:
    member_id = uuid4()
    created_at = datetime.now(UTC)
    row = {
        "id": member_id,
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": created_at,
        "last_sign_in_at": None,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        member = await queries.get_company_member(str(uuid4()), str(member_id))

    assert member is not None
    assert member.first_name == "Admin"
    connection.execute.assert_awaited_once()


async def test_update_company_member_returns_updated_member() -> None:
    member_id = uuid4()
    created_at = datetime.now(UTC)
    row = {
        "id": member_id,
        "first_name": "Updated",
        "last_name": "User",
        "email": "admin@example.com",
        "role": "inspector",
        "created_at": created_at,
        "last_sign_in_at": None,
    }
    connection = build_connection(row)

    with mock_pool(connection):
        member = await queries.update_company_member(
            str(uuid4()),
            str(member_id),
            "Updated",
            "User",
            "inspector",
        )

    assert member is not None
    assert member.role == "inspector"
    connection.execute.assert_awaited_once()


async def test_delete_company_member_returns_true_when_deleted() -> None:
    connection = build_connection({"id": uuid4()})

    with mock_pool(connection):
        was_deleted = await queries.delete_company_member(str(uuid4()), str(uuid4()))

    assert was_deleted is True
    connection.execute.assert_awaited_once()


async def test_get_company_member_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        member = await queries.get_company_member(str(uuid4()), str(uuid4()))

    assert member is None
    connection.execute.assert_awaited_once()


async def test_update_company_member_returns_none_when_missing() -> None:
    connection = build_connection(None)

    with mock_pool(connection):
        member = await queries.update_company_member(
            str(uuid4()),
            str(uuid4()),
            "Updated",
            "User",
            "inspector",
        )

    assert member is None
    connection.execute.assert_awaited_once()
