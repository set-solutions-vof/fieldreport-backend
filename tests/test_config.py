from __future__ import annotations

import os
from unittest.mock import patch

from src.config import Settings


def test_settings_loads_values_from_environment() -> None:
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test_db",
            "JWT_SECRET_KEY": "jwt-secret-for-tests-jwt-secret-for-tests",
            "JWT_ALGORITHM": "HS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "REFRESH_TOKEN_EXPIRE_DAYS": "7",
            "DEEPSEEK_ENDPOINT": "https://deepseek.example/openai/v1/",
            "DEEPSEEK_API_KEY": "deepseek-key",
            "DEEPSEEK_DEPLOYMENT": "DeepSeek-V3.2-Speciale",
            "GPT4O_ENDPOINT": "https://gpt4o.example/openai/v1/",
            "GPT4O_API_KEY": "gpt4o-key",
            "GPT4O_DEPLOYMENT": "gpt-4o",
        },
        clear=False,
    ):
        settings = Settings()

    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/test_db"
    assert settings.jwt_secret_key == "jwt-secret-for-tests-jwt-secret-for-tests"
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.deepseek_endpoint == "https://deepseek.example/openai/v1/"
    assert settings.deepseek_api_key == "deepseek-key"
    assert settings.deepseek_deployment == "DeepSeek-V3.2-Speciale"
    assert settings.gpt4o_endpoint == "https://gpt4o.example/openai/v1/"
    assert settings.gpt4o_api_key == "gpt4o-key"
    assert settings.gpt4o_deployment == "gpt-4o"
