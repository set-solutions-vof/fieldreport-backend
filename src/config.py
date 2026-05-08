from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: str = Field(validation_alias="APP_ENV")
    database_url: str = Field(validation_alias="DATABASE_URL")
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")


settings = Settings()
