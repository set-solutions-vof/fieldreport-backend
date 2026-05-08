from __future__ import annotations

import os
from unittest.mock import patch

from src.config import Settings


def test_settings_loads_values_from_environment() -> None:
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test_db"},
        clear=False,
    ):
        settings = Settings()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/test_db"
    assert settings.jwt_secret_key == "jwt-secret-for-tests-jwt-secret-for-tests"
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
