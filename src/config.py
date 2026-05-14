from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(validation_alias="APP_ENV")
    database_url: str = Field(validation_alias="DATABASE_URL")
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    deepseek_endpoint: str = Field(default="", validation_alias="DEEPSEEK_ENDPOINT")
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_deployment: str = Field(default="", validation_alias="DEEPSEEK_DEPLOYMENT")
    gpt4o_endpoint: str = Field(default="", validation_alias="GPT4O_ENDPOINT")
    gpt4o_api_key: str = Field(default="", validation_alias="GPT4O_API_KEY")
    gpt4o_deployment: str = Field(default="", validation_alias="GPT4O_DEPLOYMENT")
    gpt4o_api_version: str = Field(
        default="2024-12-01-preview", validation_alias="GPT4O_API_VERSION"
    )
    template_analysis_storage_path: str = Field(
        default=".data/template-analysis", validation_alias="TEMPLATE_ANALYSIS_STORAGE_PATH"
    )
    template_analysis_worker_poll_seconds: float = Field(
        default=2.0, validation_alias="TEMPLATE_ANALYSIS_WORKER_POLL_SECONDS"
    )


settings = Settings()
