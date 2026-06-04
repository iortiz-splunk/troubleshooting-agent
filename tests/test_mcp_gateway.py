"""Tests for MCP gateway parameter builders."""

import pytest

from troubleshooting_agent.config import Settings
from troubleshooting_agent.mcp.gateway import (
    splunk_cloud_mcp_params,
    splunk_enterprise_mcp_params,
    splunk_o11y_gateway_params,
)


def test_o11y_gateway_params() -> None:
    settings = Settings(
        splunk_o11y_gateway_url="https://example.com/mcp-gateway/v1/",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="test-token",
    )
    params = splunk_o11y_gateway_params(settings)
    assert params.command == "npx"
    assert "mcp-remote" in params.args
    assert "--silent" in params.args
    assert "X-SF-REALM:us1" in params.args
    assert "X-SF-TOKEN:test-token" in params.args
    assert not any("Authorization" in arg for arg in params.args)
    assert not any("splunk_tenant" in arg for arg in params.args)


def test_splunk_cloud_mcp_params() -> None:
    settings = Settings(
        splunk_cloud_mcp_url="https://example.com/mcp-gateway/v1/",
        splunk_cloud_mcp_bearer_token="jwt-bearer",
        splunk_cloud_mcp_tenant="my-tenant",
    )
    params = splunk_cloud_mcp_params(settings)
    assert "Authorization: Bearer jwt-bearer" in params.args
    assert "splunk_tenant:my-tenant" in params.args


def test_splunk_enterprise_mcp_params() -> None:
    settings = Settings(
        splunk_mcp_url="https://splunk.example:8089/services/mcp",
        splunk_mcp_bearer_token="bearer-token",
    )
    params = splunk_enterprise_mcp_params(settings)
    assert "Authorization: Bearer bearer-token" in params.args


def test_o11y_gateway_params_missing_token() -> None:
    with pytest.raises(ValueError, match="SPLUNK_O11Y_API_TOKEN"):
        splunk_o11y_gateway_params(
            Settings(splunk_o11y_gateway_url="https://x", splunk_o11y_realm="us1")
        )
