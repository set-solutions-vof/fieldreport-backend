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
            "AZURE_OPENAI_ENDPOINT": "https://ai.example/openai/v1/",
            "AZURE_OPENAI_API_KEY": "shared-key",
            "DEEPSEEK_DEPLOYMENT": "DeepSeek-V3.2-Speciale",
            "GPT4O_DEPLOYMENT": "gpt-4o",
            "GPT4O_TRANSCRIBE_DEPLOYMENT": "gpt-4o-transcribe",
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
    assert settings.azure_openai_endpoint == "https://ai.example/openai/v1/"
    assert settings.azure_openai_api_key == "shared-key"
    assert settings.deepseek_deployment == "DeepSeek-V3.2-Speciale"
    assert settings.gpt4o_deployment == "gpt-4o"
    assert settings.gpt4o_transcribe_deployment == "gpt-4o-transcribe"
