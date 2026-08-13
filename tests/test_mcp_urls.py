"""Tests for Splunk MCP URL normalization."""

from workshop_shared.config import Settings
from workshop_shared.mcp_urls import (
    is_direct_splunk_mcp_server_host,
    is_splunk_cloud_api_gateway_host,
    normalize_splunk_mcp_server_url,
    normalize_splunk_o11y_gateway_url,
)


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


def test_normalize_mcp_url_rewrites_legacy_gateway_path_on_direct_host() -> None:
    assert (
        normalize_splunk_mcp_server_url(
            "https://mcp-shw-60c529e5624115.stg.splunkcloud.com/system/mcp-gateway/v1/"
        )
        == "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    )


def test_normalize_o11y_gateway_url_appends_gateway_path() -> None:
    assert (
        normalize_splunk_o11y_gateway_url("https://region-pdx10.api.scs.splunk.com")
        == "https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/"
    )


def test_normalize_o11y_gateway_url_leaves_gateway_path() -> None:
    url = "https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/"
    assert normalize_splunk_o11y_gateway_url(url) == url


def test_normalize_o11y_gateway_url_does_not_rewrite_direct_mcp_host() -> None:
    url = "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    assert normalize_splunk_o11y_gateway_url(url) == url


def test_normalize_o11y_gateway_url_fixes_api_scs_direct_path() -> None:
    assert (
        normalize_splunk_o11y_gateway_url(
            "https://region-pdx10.api.scs.splunk.com:8089/services/mcp"
        )
        == "https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/"
    )


def test_settings_normalizes_cloud_mcp_url() -> None:
    host = "https://mcp-shw-60c529e5624115.stg.splunkcloud.com"
    expected = f"{host}:8089/services/mcp"

    cloud = Settings(
        enable_splunk_cloud_mcp=True,
        splunk_cloud_mcp_url=host,
        splunk_cloud_mcp_bearer_token="token",
    )
    assert cloud.splunk_cloud_mcp_url == expected


def test_settings_normalizes_o11y_gateway_url_separately() -> None:
    settings = Settings(
        splunk_o11y_gateway_url="https://region-pdx10.api.scs.splunk.com",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="token",
        splunk_cloud_mcp_url="https://mcp-shw-60c529e5624115.stg.splunkcloud.com",
        splunk_cloud_mcp_bearer_token="bearer",
    )
    assert settings.splunk_o11y_gateway_url == (
        "https://region-pdx10.api.scs.splunk.com/system/mcp-gateway/v1/"
    )
    assert settings.splunk_cloud_mcp_url == (
        "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    )
    assert settings.splunk_o11y_gateway_url != settings.splunk_cloud_mcp_url
    assert settings.enable_splunk_o11y is True


def test_gateway_host_detection() -> None:
    assert is_splunk_cloud_api_gateway_host("https://region-pdx10.api.scs.splunk.com")
    assert is_direct_splunk_mcp_server_host(
        "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    )
    assert not is_splunk_cloud_api_gateway_host(
        "https://mcp-shw-60c529e5624115.stg.splunkcloud.com:8089/services/mcp"
    )
