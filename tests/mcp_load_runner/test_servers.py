"""Tests for MCP server selection."""

import pytest

from mcp_load_runner.servers import McpServerSelection, apply_server_selection
from workshop_shared.config import Settings


def test_from_server_names() -> None:
    selection = McpServerSelection.from_server_names("o11y, cloud")
    assert selection.use_o11y is True
    assert selection.use_cloud is True


def test_from_server_names_o11y_default_style() -> None:
    selection = McpServerSelection.from_server_names("o11y")
    assert selection.use_o11y is True
    assert selection.use_cloud is False


def test_from_server_names_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown server name"):
        McpServerSelection.from_server_names("enterprise")


def test_apply_server_selection_overrides_env_flags() -> None:
    settings = Settings(
        _env_file=None,
        enable_splunk_o11y=True,
        splunk_o11y_gateway_url="https://example.com/gw",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="o11y-token",
        enable_splunk_cloud_mcp=True,
        splunk_cloud_mcp_url="https://example.com/mcp",
        splunk_cloud_mcp_bearer_token="cloud-token",
    )
    effective = apply_server_selection(
        settings,
        McpServerSelection(use_o11y=True, use_cloud=False),
    )
    assert effective.enable_splunk_o11y is True
    assert effective.enable_splunk_cloud_mcp is False
