"""Application settings loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

LlmProvider = Literal["ollama", "openai", "azure_openai"]


def _feature_enabled(requested: bool, credentials: dict[str, str | None]) -> bool:
    """Return True only when a feature is requested and all credentials are present."""
    if not requested:
        return False
    return all(credentials.values())


def default_agent_log_dir() -> str:
    """Shared investigation log directory (cwd-independent)."""
    shared_root = Path(__file__).resolve().parents[1]
    return str(shared_root / "logs" / "investigations")


# ---------------------------------------------------------------------------
# Settings model
# All env vars (.env) for LLM, MCP, Slack, logging, OTel, and Galileo.
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    """Configuration for the troubleshooting agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        env_ignore_empty=True,
    )

    llm_provider: LlmProvider | None = Field(
        default=None,
        description=(
            "LLM backend: ollama, openai, or azure_openai (auto-detected from env if unset)"
        ),
    )
    llm_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for troubleshooting",
        validation_alias=AliasChoices("llm_temperature", "LLM_TEMPERATURE", "OLLAMA_TEMPERATURE"),
    )

    ollama_base_url: str = Field(
        default="http://127.0.0.1:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="qwen2.5-coder:7b",
        description="Ollama model name",
    )

    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI-compatible API key (OPENAI_API_KEY)",
        validation_alias=AliasChoices("openai_api_key", "OPENAI_API_KEY"),
    )
    openai_base_url: str | None = Field(
        default=None,
        description="OpenAI-compatible base URL, e.g. LiteLLM proxy /v1 endpoint",
        validation_alias=AliasChoices("openai_base_url", "OPENAI_BASE_URL"),
    )
    openai_model_name: str = Field(
        default="gpt-4.1-mini",
        description="Model name for OpenAI-compatible APIs",
        validation_alias=AliasChoices("openai_model_name", "OPENAI_MODEL_NAME"),
    )

    azure_openai_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI resource endpoint URL",
    )
    azure_openai_api_key: str | None = Field(
        default=None,
        description="Azure OpenAI API key",
    )
    azure_openai_deployment_name: str | None = Field(
        default=None,
        description="Azure OpenAI deployment name",
    )
    azure_openai_api_version: str | None = Field(
        default=None,
        description="Azure OpenAI API version, e.g. 2024-10-21",
    )

    # MCP transport (mcp-remote via npx, matching Cursor)
    mcp_npx_command: str = Field(default="npx", description="Command to run mcp-remote")
    mcp_allow_http: bool = Field(
        default=True,
        description="Pass --transport http-only --allow-http to mcp-remote",
    )

    # Splunk Observability Cloud (o11y tools on Splunk Cloud MCP gateway)
    enable_splunk_o11y: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_splunk_o11y", "ENABLE_SPLUNK_O11Y"),
    )
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
    enable_splunk_cloud_mcp: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_splunk_cloud_mcp", "ENABLE_SPLUNK_CLOUD_MCP"),
    )
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
    enable_splunk_mcp: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_splunk_mcp", "ENABLE_SPLUNK_MCP"),
    )
    splunk_mcp_url: str | None = Field(
        default=None,
        description="Splunk Enterprise MCP endpoint URL",
    )
    splunk_mcp_bearer_token: str | None = Field(
        default=None,
        description="Bearer token for Splunk Enterprise MCP",
    )

    # Slack demo (Socket Mode listener for Observability alerts channel)
    enable_slack: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_slack", "ENABLE_SLACK"),
    )
    slack_bot_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_bot_token", "SLACK_BOT_TOKEN"),
    )
    slack_app_token: str | None = Field(
        default=None,
        description="App-level token for Socket Mode (xapp-...)",
        validation_alias=AliasChoices("slack_app_token", "SLACK_APP_TOKEN"),
    )
    slack_signing_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices("slack_signing_secret", "SLACK_SIGNING_SECRET"),
    )
    slack_alerts_channel_name: str = Field(
        default="splunk-observability-alerts-1",
        description="Public channel name for Observability alert posts (without #)",
        validation_alias=AliasChoices(
            "slack_alerts_channel_name",
            "SLACK_ALERTS_CHANNEL_NAME",
        ),
    )
    slack_alerts_channel_id: str | None = Field(
        default=None,
        description="Optional channel ID (C...); skips name lookup when set",
        validation_alias=AliasChoices("slack_alerts_channel_id", "SLACK_ALERTS_CHANNEL_ID"),
    )

    # Agent logging trace (terminal)
    agent_log_trace: bool = Field(
        default=True,
        description="Brief INFO logs for agent/MCP activity",
        validation_alias=AliasChoices("agent_log_trace", "AGENT_LOG_TRACE"),
    )
    agent_log_debug: bool = Field(
        default=False,
        description="Verbose tool args in logs (workshop only)",
        validation_alias=AliasChoices("agent_log_debug", "AGENT_LOG_DEBUG"),
    )
    log_format: Literal["text", "json"] = Field(
        default="text",
        description="Log format: text or json",
        validation_alias=AliasChoices("log_format", "LOG_FORMAT"),
    )
    agent_log_dir: str | None = Field(
        default_factory=default_agent_log_dir,
        description="Directory for per-investigation JSONL trace files (empty to disable)",
        validation_alias=AliasChoices("agent_log_dir", "AGENT_LOG_DIR"),
    )

    # Splunk OTel (APM traces — direct ingest; separate from o11y MCP API token)
    enable_splunk_otel: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_splunk_otel", "ENABLE_SPLUNK_OTEL"),
    )
    otel_service_name: str = Field(
        default="troubleshooting-agent",
        validation_alias=AliasChoices("otel_service_name", "OTEL_SERVICE_NAME"),
    )
    splunk_access_token: str | None = Field(
        default=None,
        description="Splunk ingest token for OTel (SPLUNK_ACCESS_TOKEN)",
        validation_alias=AliasChoices("splunk_access_token", "SPLUNK_ACCESS_TOKEN"),
    )

    # Galileo agent observability
    enable_galileo: bool = Field(
        default=False,
        validation_alias=AliasChoices("enable_galileo", "ENABLE_GALILEO"),
    )
    galileo_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("galileo_api_key", "GALILEO_API_KEY"),
    )
    galileo_project: str = Field(
        default="troubleshooting-agent",
        validation_alias=AliasChoices("galileo_project", "GALILEO_PROJECT"),
    )
    galileo_log_stream: str = Field(
        default="slack-investigations",
        validation_alias=AliasChoices("galileo_log_stream", "GALILEO_LOG_STREAM"),
    )
    galileo_console_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("galileo_console_url", "GALILEO_CONSOLE_URL"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Shell/process env wins over .env (workshop EC2 injects secrets there).
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @model_validator(mode="after")
    def validate_llm_and_mcp_settings(self) -> "Settings":
        if self.llm_provider is None:
            if self.openai_api_key and self.openai_base_url:
                self.llm_provider = "openai"
            elif (
                self.azure_openai_endpoint
                and self.azure_openai_api_key
                and self.azure_openai_deployment_name
                and self.azure_openai_api_version
            ):
                self.llm_provider = "azure_openai"
            else:
                self.llm_provider = "ollama"

        if self.llm_provider == "openai":
            missing = [
                name
                for name, value in [
                    ("OPENAI_API_KEY", self.openai_api_key),
                    ("OPENAI_BASE_URL", self.openai_base_url),
                ]
                if not value
            ]
            if missing:
                msg = f"llm_provider=openai requires: {', '.join(missing)}"
                raise ValueError(msg)
        if self.llm_provider == "azure_openai":
            missing = [
                name
                for name, value in [
                    ("AZURE_OPENAI_ENDPOINT", self.azure_openai_endpoint),
                    ("AZURE_OPENAI_API_KEY", self.azure_openai_api_key),
                    ("AZURE_OPENAI_DEPLOYMENT_NAME", self.azure_openai_deployment_name),
                    ("AZURE_OPENAI_API_VERSION", self.azure_openai_api_version),
                ]
                if not value
            ]
            if missing:
                msg = f"llm_provider=azure_openai requires: {', '.join(missing)}"
                raise ValueError(msg)
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
        else:
            o11y_credentials = {
                "SPLUNK_O11Y_GATEWAY_URL": self.splunk_o11y_gateway_url,
                "SPLUNK_O11Y_REALM": self.splunk_o11y_realm,
                "SPLUNK_O11Y_API_TOKEN": self.splunk_o11y_api_token,
            }
            if all(o11y_credentials.values()):
                self.enable_splunk_o11y = True
        self.enable_splunk_cloud_mcp = _feature_enabled(
            self.enable_splunk_cloud_mcp,
            {
                "SPLUNK_CLOUD_MCP_URL": self.splunk_cloud_mcp_url,
                "SPLUNK_CLOUD_MCP_BEARER_TOKEN": self.splunk_cloud_mcp_bearer_token,
            },
        )
        self.enable_splunk_mcp = _feature_enabled(
            self.enable_splunk_mcp,
            {
                "SPLUNK_MCP_URL": self.splunk_mcp_url,
                "SPLUNK_MCP_BEARER_TOKEN": self.splunk_mcp_bearer_token,
            },
        )
        self.enable_slack = _feature_enabled(
            self.enable_slack,
            {
                "SLACK_BOT_TOKEN": self.slack_bot_token,
                "SLACK_APP_TOKEN": self.slack_app_token,
                "SLACK_SIGNING_SECRET": self.slack_signing_secret,
            },
        )
        self.enable_splunk_otel = _feature_enabled(
            self.enable_splunk_otel,
            {"SPLUNK_ACCESS_TOKEN": self.splunk_access_token},
        )
        if self.enable_galileo:
            missing = [
                name
                for name, value in [
                    ("GALILEO_API_KEY", self.galileo_api_key),
                    ("GALILEO_CONSOLE_URL", self.galileo_console_url),
                ]
                if not value
            ]
            if missing:
                msg = f"enable_galileo requires: {', '.join(missing)}"
                raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Settings loader
# Walks up from cwd to find .env so parts can run from part1_agent/, etc.
# ---------------------------------------------------------------------------
def get_settings() -> Settings:
    """Load settings from environment, finding .env by walking up from cwd."""
    from workshop_shared.env_hydration import hydrate_workshop_env
    from workshop_shared.workshop_context import find_env_file

    hydrate_workshop_env()
    env_file = find_env_file()
    if env_file is not None:
        return Settings(_env_file=env_file)
    return Settings()
