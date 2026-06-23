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

    generation_output_dir: str = Field(default="./generated_output")

    # AI / documentation flow settings
    # Set to "crewai" to use the CrewAI-backed flow; "fallback" requires no API keys.
    ai_documentation_provider: str = Field(default="fallback")
    anthropic_api_key: str | None = Field(default=None)
    openai_api_key: str | None = Field(default=None)
    ai_model: str | None = Field(default=None)


settings = Settings()
