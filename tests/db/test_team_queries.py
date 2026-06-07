from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.db import team_queries
from src.models.team.member import TeamMember


def build_connection(rows: list[dict[str, object]]) -> SimpleNamespace:
    return SimpleNamespace(
        fetch=AsyncMock(return_value=rows),
    )


def mock_pool(connection):
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("src.db.team_queries.get_pool", return_value=pool)


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
    connection = build_connection([row])

    with mock_pool(connection):
        members = await team_queries.list_company_members(str(uuid4()))

    assert members == [
        TeamMember(
            id=member_id,
            name="Admin",
            email="admin@example.com",
            role="admin",
            created_at=created_at,
        )
    ]
