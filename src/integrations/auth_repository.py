import asyncpg

from src.config import settings
from src.models.auth.authentication import AuthenticatedUser, CurrentUser


def get_database_connection_url() -> str:
    return settings.database_url.replace("+asyncpg", "")


def map_authenticated_user(row: asyncpg.Record) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=row["id"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        email=row["email"],
        password_hash=row["password_hash"],
        name=row["name"],
        role=row["role"],
    )


def map_current_user(row: asyncpg.Record) -> CurrentUser:
    return CurrentUser(
        id=row["id"],
        company_id=row["company_id"],
        company_name=row["company_name"],
        email=row["email"],
        name=row["name"],
        role=row["role"],
    )


async def get_user_by_email(email: str) -> AuthenticatedUser | None:
    connection = await asyncpg.connect(get_database_connection_url())

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
    connection = await asyncpg.connect(get_database_connection_url())

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
