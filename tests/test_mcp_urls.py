"""Tests for Splunk MCP URL normalization."""

from workshop_shared.config import Settings
from workshop_shared.mcp_urls import normalize_splunk_mcp_server_url


def test_normalize_mcp_url_appends_port_and_path_from_host() -> None:
    assert (
        normalize_splunk_mcp_server_url("https://mcp-shw-60c529e5624115.stg.splunkcloud.com")
        == "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    )


def test_normalize_mcp_url_appends_path_when_port_present() -> None:
    assert (
        normalize_splunk_mcp_server_url("https://splunk.example:8089")
        == "https://splunk.example:8089/services/mcp"
    )


def test_normalize_mcp_url_leaves_complete_url() -> None:
    url = "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    assert normalize_splunk_mcp_server_url(url) == url


def test_normalize_mcp_url_rewrites_legacy_gateway_path() -> None:
    assert (
        normalize_splunk_mcp_server_url("https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/")
        == "https://region-pdx10.api.scs.splunk.com:8089/services/mcp"
    )


def test_settings_normalizes_cloud_and_o11y_urls() -> None:
    host = "https://mcp-shw-60c529e5624115.stg.splunkcloud.com"
    expected = f"{host}:8089/services/mcp"

    cloud = Settings(
        enable_splunk_cloud_mcp=True,
        splunk_cloud_mcp_url=host,
        splunk_cloud_mcp_bearer_token="token",
    )
    assert cloud.splunk_cloud_mcp_url == expected

    o11y = Settings(
        splunk_o11y_gateway_url=host,
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="token",
    )
    assert o11y.splunk_o11y_gateway_url == expected
    assert o11y.enable_splunk_o11y is True
