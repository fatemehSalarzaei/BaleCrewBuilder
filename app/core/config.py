from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me")

    database_url: str = Field(
        default="postgresql+asyncpg://builder:builder@localhost:5432/builder"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    log_level: str = Field(default="INFO")


settings = Settings()
