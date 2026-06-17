from datetime import datetime
from typing import Any

import sqlalchemy as sa

from src.db.connection import get_database
from src.db.schema.tables import password_reset_tokens


async def create_reset_token(user_id: str, token_hash: str, expires_at: datetime) -> None:
    statement = password_reset_tokens.insert().values(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def get_valid_reset_token(token_hash: str) -> dict[str, Any] | None:
    statement = sa.select(
        password_reset_tokens.c.id,
        password_reset_tokens.c.user_id,
    ).where(
        password_reset_tokens.c.token_hash == token_hash,
        password_reset_tokens.c.expires_at > sa.func.now(),
        password_reset_tokens.c.used_at.is_(None),
    )

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        row = result.mappings().first()

    if row is None:
        return None

    return dict(row)


async def mark_token_used(token_id: str) -> None:
    statement = (
        password_reset_tokens.update()
        .where(password_reset_tokens.c.id == token_id)
        .values(used_at=sa.func.now())
    )

    async with get_database().acquire() as connection:
        await connection.execute(statement)
