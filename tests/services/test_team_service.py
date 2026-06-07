from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.team.member import TeamMember
from src.services import team as team_service


async def test_list_team_members_returns_members() -> None:
    member = TeamMember(
        id=uuid4(),
        name="Admin",
        email="admin@example.com",
        role="admin",
        created_at=datetime.now(UTC),
    )

    with patch.object(
        team_service.team_queries,
        "list_company_members",
        AsyncMock(return_value=[member]),
    ):
        result = await team_service.list_team_members(str(uuid4()))

    assert result == [member]
