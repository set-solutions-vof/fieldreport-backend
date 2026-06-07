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
            "SMTP_HOST": "smtp.office365.com",
            "SMTP_PORT": "587",
            "SMTP_USE_STARTTLS": "true",
            "SMTP_USERNAME": "smtp-user",
            "SMTP_PASSWORD": "smtp-pass",
            "SMTP_FROM_EMAIL": "no-reply@example.com",
            "SMTP_FROM_NAME": "FieldReport",
            "FRONTEND_BASE_URL": "http://localhost:5173",
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
    assert settings.smtp_host == "smtp.office365.com"
    assert settings.smtp_port == 587
    assert settings.smtp_use_starttls is True
    assert settings.smtp_username == "smtp-user"
    assert settings.smtp_password == "smtp-pass"
    assert settings.smtp_from_email == "no-reply@example.com"
    assert settings.smtp_from_name == "FieldReport"
    assert settings.frontend_base_url == "http://localhost:5173"
