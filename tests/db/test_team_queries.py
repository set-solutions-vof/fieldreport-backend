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
        "name": "Admin",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": created_at,
    }
    connection = build_connection(rows=[row])

    with mock_pool(connection):
        members = await queries.list_company_members(str(uuid4()))

    assert members == [
        TeamMember(
            id=member_id,
            name="Admin",
            email="admin@example.com",
            role="admin",
            created_at=created_at,
        )
    ]
    connection.execute.assert_awaited_once()
