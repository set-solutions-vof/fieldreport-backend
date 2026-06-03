import asyncpg

from src.config import settings

_pool: asyncpg.Pool


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(settings.database_url.replace("+asyncpg", ""))


async def close_pool() -> None:
    await _pool.close()


def get_pool() -> asyncpg.Pool:
    return _pool
