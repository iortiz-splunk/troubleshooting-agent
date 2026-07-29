"""Tests for application settings."""

import pytest

from workshop_shared.config import Settings, default_agent_log_dir


def test_settings_defaults() -> None:
    settings = Settings()
    assert settings.llm_provider == "ollama"
    assert settings.ollama_base_url == "http://127.0.0.1:11434"
    assert settings.ollama_model == "qwen2.5-coder:7b"
    assert settings.llm_temperature == 0.2
    assert settings.enable_splunk_o11y is False
    assert settings.splunk_o11y_tool_prefix == "o11y_"
    assert settings.agent_log_dir == default_agent_log_dir()
    assert settings.agent_log_dir.endswith("shared/logs/investigations")


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    settings = Settings()
    assert settings.ollama_model == "qwen2.5:7b"
    assert settings.ollama_base_url == "http://localhost:11434"


def test_enable_o11y_requires_credentials() -> None:
    with pytest.raises(ValueError, match="SPLUNK_O11Y"):
        Settings(enable_splunk_o11y=True)


def test_enable_o11y_auto_enables_when_credentials_present() -> None:
    settings = Settings(
        splunk_o11y_gateway_url="https://gw.example/",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="token",
    )
    assert settings.enable_splunk_o11y is True


def test_auto_detect_openai_provider() -> None:
    settings = Settings(
        openai_api_key="key",
        openai_base_url="https://lite-llm-proxy.splunko11y.com/v1",
    )
    assert settings.llm_provider == "openai"


def test_explicit_ollama_overrides_openai_env() -> None:
    settings = Settings(
        llm_provider="ollama",
        openai_api_key="key",
        openai_base_url="https://lite-llm-proxy.example.com/v1",
    )
    assert settings.llm_provider == "ollama"


def test_openai_requires_credentials() -> None:
    with pytest.raises(ValueError, match="OPENAI"):
        Settings(llm_provider="openai")


def test_openai_settings_valid() -> None:
    settings = Settings(
        llm_provider="openai",
        openai_api_key="key",
        openai_base_url="https://lite-llm-proxy.splunko11y.com/v1",
    )
    assert settings.llm_provider == "openai"
    assert settings.openai_model_name == "gpt-4.1-mini"


def test_azure_openai_requires_credentials() -> None:
    with pytest.raises(ValueError, match="AZURE_OPENAI"):
        Settings(llm_provider="azure_openai")


def test_enable_slack_disabled_when_credentials_missing() -> None:
    settings = Settings(enable_slack=True)
    assert settings.enable_slack is False


def test_enable_slack_stays_enabled_with_credentials() -> None:
    settings = Settings(
        enable_slack=True,
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_signing_secret="secret",
    )
    assert settings.enable_slack is True


def test_enable_slack_settings_valid() -> None:
    settings = Settings(
        enable_slack=True,
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_signing_secret="secret",
    )
    assert settings.slack_alerts_channel_name == "splunk-observability-alerts-1"
    assert settings.agent_log_trace is True


def test_enable_splunk_mcp_disabled_when_credentials_missing() -> None:
    settings = Settings(enable_splunk_mcp=True)
    assert settings.enable_splunk_mcp is False


def test_enable_splunk_cloud_mcp_disabled_when_credentials_missing() -> None:
    settings = Settings(enable_splunk_cloud_mcp=True)
    assert settings.enable_splunk_cloud_mcp is False


def test_enable_splunk_otel_enabled_without_ingest_token() -> None:
    settings = Settings(enable_splunk_otel=True)
    assert settings.enable_splunk_otel is True
    assert settings.otel_collector_endpoint == "http://localhost:4318"


def test_enable_splunk_otel_custom_collector_endpoint() -> None:
    settings = Settings(
        enable_splunk_otel=True,
        otel_collector_endpoint="http://127.0.0.1:4318",
    )
    assert settings.otel_collector_endpoint == "http://127.0.0.1:4318"


def test_empty_enable_flags_default_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_SLACK", "")
    monkeypatch.setenv("ENABLE_SPLUNK_MCP", "")
    settings = Settings(_env_file=None)
    assert settings.enable_slack is False
    assert settings.enable_splunk_mcp is False


def test_openai_placeholder_base_url_is_ignored() -> None:
    settings = Settings(
        openai_api_key="real-key",
        openai_base_url="https://lite-llm-proxy.example.com/v1",
    )
    assert settings.openai_base_url is None
    assert settings.llm_provider == "ollama"


def test_openai_real_base_url_is_kept() -> None:
    settings = Settings(
        openai_api_key="real-key",
        openai_base_url="https://lite-llm-proxy.splunko11y.com/v1",
    )
    assert settings.llm_provider == "openai"
    assert settings.openai_base_url == "https://lite-llm-proxy.splunko11y.com/v1"


def test_enable_galileo_requires_api_key() -> None:
    with pytest.raises(ValueError, match="GALILEO_API_KEY"):
        Settings(enable_galileo=True)


def test_enable_galileo_requires_console_url() -> None:
    with pytest.raises(ValueError, match="GALILEO_CONSOLE_URL"):
        Settings(enable_galileo=True, galileo_api_key="key")


def test_azure_openai_settings_valid() -> None:
    settings = Settings(
        llm_provider="azure_openai",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="key",
        azure_openai_deployment_name="gpt-4o",
        azure_openai_api_version="2024-10-21",
    )
    assert settings.llm_provider == "azure_openai"
    assert settings.azure_openai_deployment_name == "gpt-4o"
