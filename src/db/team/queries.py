import sqlalchemy as sa

from src.db.connection import get_database
from src.db.schema.tables import users
from src.db.team.mapper import map_team_member
from src.models.team.member import TeamMember


async def list_company_members(company_id: str) -> list[TeamMember]:
    statement = (
        sa.select(
            users.c.id,
            users.c.name,
            users.c.email,
            users.c.role,
            users.c.created_at,
        )
        .where(users.c.company_id == company_id)
        .order_by(users.c.created_at.asc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_team_member(row) for row in rows]
