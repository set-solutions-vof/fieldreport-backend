import sqlalchemy as sa

from src.db.connection import get_database
from src.db.schema.tables import users
from src.db.team.mapper import map_team_member
from src.models.team.member import TeamMember


async def list_company_members(company_id: str) -> list[TeamMember]:
    statement = (
        sa.select(
            users.c.id,
            users.c.first_name,
            users.c.last_name,
            users.c.email,
            users.c.role,
            users.c.created_at,
            users.c.last_sign_in_at,
        )
        .where(users.c.company_id == company_id)
        .order_by(users.c.created_at.asc())
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        rows = result.mappings().all()

    return [map_team_member(row) for row in rows]


async def get_company_member(company_id: str, member_id: str) -> TeamMember | None:
    statement = sa.select(
        users.c.id,
        users.c.first_name,
        users.c.last_name,
        users.c.email,
        users.c.role,
        users.c.created_at,
        users.c.last_sign_in_at,
    ).where(users.c.id == member_id, users.c.company_id == company_id)

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_team_member(row)


async def update_company_member(
    company_id: str,
    member_id: str,
    first_name: str,
    last_name: str,
    role: str,
) -> TeamMember | None:
    statement = (
        users.update()
        .where(users.c.id == member_id, users.c.company_id == company_id)
        .values(first_name=first_name, last_name=last_name, role=role)
        .returning(
            users.c.id,
            users.c.first_name,
            users.c.last_name,
            users.c.email,
            users.c.role,
            users.c.created_at,
            users.c.last_sign_in_at,
        )
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_team_member(row)


async def delete_company_member(company_id: str, member_id: str) -> bool:
    statement = (
        users.delete()
        .where(users.c.id == member_id, users.c.company_id == company_id)
        .returning(users.c.id)
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    return row is not None
