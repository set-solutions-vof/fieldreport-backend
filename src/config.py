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
    azure_openai_endpoint: str = Field(default="", validation_alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_resource_endpoint: str = Field(
        default="", validation_alias="AZURE_OPENAI_RESOURCE_ENDPOINT"
    )
    azure_openai_api_key: str = Field(default="", validation_alias="AZURE_OPENAI_API_KEY")
    deepseek_deployment: str = Field(default="", validation_alias="DEEPSEEK_DEPLOYMENT")
    gpt4o_deployment: str = Field(default="", validation_alias="GPT4O_DEPLOYMENT")
    gpt4o_transcribe_deployment: str = Field(
        default="gpt-4o-transcribe", validation_alias="GPT4O_TRANSCRIBE_DEPLOYMENT"
    )
    gpt4o_transcribe_api_version: str = Field(
        default="2024-10-21", validation_alias="GPT4O_TRANSCRIBE_API_VERSION"
    )
    template_analysis_worker_poll_seconds: float = Field(
        default=2.0, validation_alias="TEMPLATE_ANALYSIS_WORKER_POLL_SECONDS"
    )
    audio_pipeline_worker_poll_seconds: float = Field(
        default=5.0, validation_alias="AUDIO_PIPELINE_WORKER_POLL_SECONDS"
    )
    azure_storage_connection_string: str = Field(
        default="", validation_alias="AZURE_STORAGE_CONNECTION_STRING"
    )


settings = Settings()
