from unittest.mock import patch

from src.db import connection


def test_get_connection_url_strips_asyncpg_driver() -> None:
    with patch.object(
        connection.settings,
        "database_url",
        "postgresql+asyncpg://fieldreport:fieldreport@localhost:5432/fieldreport_test",
    ):
        result = connection.get_connection_url()

    assert result == "postgresql://fieldreport:fieldreport@localhost:5432/fieldreport_test"
