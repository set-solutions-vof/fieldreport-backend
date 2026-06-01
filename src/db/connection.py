from src.config import settings


def get_connection_url() -> str:
    return settings.database_url.replace("+asyncpg", "")
