from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(..., env="APP_ENV")
    database_url: str = Field(..., env="DATABASE_URL")


settings = Settings()
