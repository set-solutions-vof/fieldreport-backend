from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from src.config import settings

_engine: AsyncEngine


class DatabaseConnection:
    def __init__(self, connection: AsyncConnection) -> None:
        self.connection = connection

    async def execute(self, statement, parameters: dict | list[dict] | None = None):
        return await self.connection.execute(statement, parameters)

    def transaction(self):
        return self.connection.begin()


class Database:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[DatabaseConnection]:
        async with self.engine.connect() as connection:
            try:
                yield DatabaseConnection(connection)
                await connection.commit()
            except Exception:
                await connection.rollback()
                raise


def database_url() -> str:
    return settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


async def init_database() -> None:
    global _engine
    _engine = create_async_engine(
        database_url(),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=5,
    )


async def close_database() -> None:
    await _engine.dispose()


def get_database() -> Database:
    return Database(_engine)
