import asyncpg

from src.models.auth.authentication import AuthenticatedUser, CurrentUser


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
