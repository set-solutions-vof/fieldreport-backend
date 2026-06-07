from src.db.connection import get_pool
from src.db.team_mapper import map_team_member
from src.models.team.member import TeamMember


async def list_company_members(company_id: str) -> list[TeamMember]:
    async with get_pool().acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            WHERE company_id = $1::uuid
            ORDER BY created_at ASC
            """,
            company_id,
        )

    return [map_team_member(row) for row in rows]
