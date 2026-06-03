"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the troubleshooting agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="qwen2.5-coder:7b",
        description="Ollama model name",
    )
    ollama_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for troubleshooting",
    )

    # Future integration flags (Phase 1+)
    enable_splunk_o11y: bool = Field(default=False)
    enable_splunk_mcp: bool = Field(default=False)
    enable_slack: bool = Field(default=False)

    # Future credentials (unused in Phase 0)
    splunk_o11y_api_token: str | None = None
    splunk_o11y_realm: str | None = None
    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None


def get_settings() -> Settings:
    """Load settings from environment."""
    return Settings()
