import sqlalchemy as sa

from src.db.auth.mapper import map_authenticated_user, map_current_user
from src.db.connection import get_database
from src.db.schema.tables import company, users
from src.models.auth.authentication import AuthenticatedUser, CurrentUser


def _user_company_select():
    return sa.select(
        users.c.id,
        users.c.company_id,
        company.c.name.label("company_name"),
        users.c.email,
        users.c.name,
        users.c.role,
    ).select_from(users.join(company, company.c.id == users.c.company_id))


async def get_user_by_email(email: str) -> AuthenticatedUser | None:
    statement = (
        _user_company_select().add_columns(users.c.password_hash).where(users.c.email == email)
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_authenticated_user(row)


async def get_user_by_id(user_id: str) -> CurrentUser | None:
    statement = _user_company_select().where(users.c.id == user_id)

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return map_current_user(row)
