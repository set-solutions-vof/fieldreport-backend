from datetime import UTC, datetime
from uuid import uuid4

from src.db.team.mapper import map_team_member
from src.models.team.member import TeamMember


def test_map_team_member_parses_record() -> None:
    member_id = uuid4()
    created_at = datetime.now(UTC)

    member = map_team_member(
        {
            "id": member_id,
            "name": "Admin",
            "email": "admin@example.com",
            "role": "admin",
            "created_at": created_at,
        }
    )

    assert member == TeamMember(
        id=member_id,
        name="Admin",
        email="admin@example.com",
        role="admin",
        created_at=created_at,
    )
