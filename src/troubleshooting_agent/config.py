"""Application settings loaded from environment variables."""

from pydantic import Field, model_validator
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

    # MCP transport (mcp-remote via npx, matching Cursor)
    mcp_npx_command: str = Field(default="npx", description="Command to run mcp-remote")
    mcp_allow_http: bool = Field(
        default=True,
        description="Pass --transport http-only --allow-http to mcp-remote",
    )

    # Splunk Observability Cloud (o11y tools on Splunk Cloud MCP gateway)
    enable_splunk_o11y: bool = Field(default=False)
    splunk_o11y_gateway_url: str | None = Field(
        default=None,
        description="Splunk Cloud MCP gateway URL for Observability tools",
    )
    splunk_o11y_realm: str | None = Field(default=None, description="Observability realm, e.g. us1")
    splunk_o11y_api_token: str | None = Field(
        default=None,
        description="Observability API access token (X-SF-TOKEN)",
    )
    splunk_o11y_tool_prefix: str = Field(
        default="o11y_",
        description="Only expose MCP tools whose names start with this prefix",
    )

    # Splunk Cloud MCP server (platform / logs — not Observability-only auth)
    enable_splunk_cloud_mcp: bool = Field(default=False)
    splunk_cloud_mcp_url: str | None = Field(
        default=None,
        description="Splunk Cloud MCP gateway or server URL",
    )
    splunk_cloud_mcp_bearer_token: str | None = Field(
        default=None,
        description="Splunk Cloud MCP Bearer token (encrypted JWT from MCP app)",
    )
    splunk_cloud_mcp_tenant: str | None = Field(
        default=None,
        description="Splunk Cloud tenant name (splunk_tenant header)",
    )

    # Splunk Enterprise MCP (on-prem)
    enable_splunk_mcp: bool = Field(default=False)
    splunk_mcp_url: str | None = Field(
        default=None,
        description="Splunk Enterprise MCP endpoint URL",
    )
    splunk_mcp_bearer_token: str | None = Field(
        default=None,
        description="Bearer token for Splunk Enterprise MCP",
    )

    # Slack (Phase 3)
    enable_slack: bool = Field(default=False)
    slack_bot_token: str | None = None
    slack_signing_secret: str | None = None

    @model_validator(mode="after")
    def validate_mcp_settings(self) -> "Settings":
        if self.enable_splunk_o11y:
            missing = [
                name
                for name, value in [
                    ("SPLUNK_O11Y_GATEWAY_URL", self.splunk_o11y_gateway_url),
                    ("SPLUNK_O11Y_REALM", self.splunk_o11y_realm),
                    ("SPLUNK_O11Y_API_TOKEN", self.splunk_o11y_api_token),
                ]
                if not value
            ]
            if missing:
                msg = f"enable_splunk_o11y requires: {', '.join(missing)}"
                raise ValueError(msg)
        if self.enable_splunk_cloud_mcp:
            missing = [
                name
                for name, value in [
                    ("SPLUNK_CLOUD_MCP_URL", self.splunk_cloud_mcp_url),
                    ("SPLUNK_CLOUD_MCP_BEARER_TOKEN", self.splunk_cloud_mcp_bearer_token),
                ]
                if not value
            ]
            if missing:
                msg = f"enable_splunk_cloud_mcp requires: {', '.join(missing)}"
                raise ValueError(msg)
        if self.enable_splunk_mcp:
            missing = [
                name
                for name, value in [
                    ("SPLUNK_MCP_URL", self.splunk_mcp_url),
                    ("SPLUNK_MCP_BEARER_TOKEN", self.splunk_mcp_bearer_token),
                ]
                if not value
            ]
            if missing:
                msg = f"enable_splunk_mcp requires: {', '.join(missing)}"
                raise ValueError(msg)
        return self


def get_settings() -> Settings:
    """Load settings from environment."""
    return Settings()
