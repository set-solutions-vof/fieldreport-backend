import asyncpg

from src.db.auth_mapper import map_authenticated_user, map_current_user
from src.db.connection import get_connection_url
from src.models.auth.authentication import AuthenticatedUser, CurrentUser


async def get_user_by_email(email: str) -> AuthenticatedUser | None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT
                users.id,
                users.company_id,
                company.name AS company_name,
                email,
                password_hash,
                users.name,
                role
            FROM users
            JOIN company ON company.id = users.company_id
            WHERE email = $1
            """,
            email,
        )
    finally:
        await connection.close()

    if row is None:
        return None

    return map_authenticated_user(row)


async def get_user_by_id(user_id: str) -> CurrentUser | None:
    connection = await asyncpg.connect(get_connection_url())

    try:
        row = await connection.fetchrow(
            """
            SELECT
                users.id,
                users.company_id,
                company.name AS company_name,
                email,
                users.name,
                role
            FROM users
            JOIN company ON company.id = users.company_id
            WHERE users.id = $1::uuid
            """,
            user_id,
        )
    finally:
        await connection.close()

    if row is None:
        return None

    return map_current_user(row)
