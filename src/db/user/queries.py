import sqlalchemy as sa

from src.db.connection import get_database
from src.db.schema.tables import users


async def get_user_password_hash(user_id: str) -> str:
    statement = sa.select(users.c.password_hash).where(users.c.id == user_id)

    async with get_database().acquire() as connection:
        result = await connection.execute(statement)
        password_hash = result.scalar_one_or_none()

    if password_hash is None:
        raise RuntimeError("Authenticated user not found")

    return password_hash


async def update_user_name(user_id: str, name: str) -> None:
    statement = sa.update(users).where(users.c.id == user_id).values(name=name)

    async with get_database().acquire() as connection:
        await connection.execute(statement)


async def update_user_password(user_id: str, password_hash: str) -> None:
    statement = sa.update(users).where(users.c.id == user_id).values(password_hash=password_hash)

    async with get_database().acquire() as connection:
        await connection.execute(statement)
