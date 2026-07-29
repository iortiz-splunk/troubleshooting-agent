"""Tests for MCP load test diagnostics and preflight hints."""

import logging
from unittest.mock import patch

import pytest

from mcp_load_runner.diagnostics import MemoryLogHandler, build_preflight_hints, summarize_settings
from mcp_load_runner.preflight import run_preflight
from mcp_load_runner.scenarios import required_tool_names
from mcp_load_runner.servers import McpServerSelection
from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import McpServerInfo


def _test_settings(**overrides: object) -> Settings:
    base = {
        "_env_file": None,
        "enable_splunk_o11y": True,
        "splunk_o11y_gateway_url": "https://example.com/gw",
        "splunk_o11y_realm": "us1",
        "splunk_o11y_api_token": "o11y-token",
        "enable_splunk_cloud_mcp": True,
        "splunk_cloud_mcp_url": "https://example.com/mcp",
        "splunk_cloud_mcp_bearer_token": "cloud-token",
    }
    base.update(overrides)
    return Settings(**base)


def test_memory_log_handler_initializes() -> None:
    handler = MemoryLogHandler()
    assert hasattr(handler, "filters")
    assert handler.level == logging.NOTSET

    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.handle(logging.LogRecord("test", logging.INFO, "", 0, "hello", (), None))
    assert handler.lines == ["hello"]


def test_summarize_settings_masks_secrets() -> None:
    settings = _test_settings(
        enable_splunk_cloud_mcp=True,
        enable_splunk_o11y=False,
        splunk_o11y_gateway_url=None,
        splunk_o11y_realm=None,
        splunk_o11y_api_token=None,
        splunk_cloud_mcp_url="https://example.splunkcloud.com/mcp/v1/",
        splunk_cloud_mcp_bearer_token="super-secret-jwt",
        splunk_cloud_mcp_tenant="my-tenant",
    )
    lines = summarize_settings(settings, env_file="/repo/.env")
    joined = "\n".join(lines)
    assert "super-secret-jwt" not in joined
    assert "set (" in joined and "chars)" in joined
    assert "example.splunkcloud.com" in joined
    assert "my-tenant" in joined


def test_build_preflight_hints_zero_cloud_tools() -> None:
    servers = [
        McpServerInfo(name="splunk_o11y", ok=True, tool_count=12, tool_names=["o11y_foo"]),
        McpServerInfo(name="splunk_cloud_mcp", ok=True, tool_count=0, tool_names=[]),
    ]
    settings = _test_settings()
    hints = build_preflight_hints(
        servers,
        missing_tools=["splunk_run_query"],
        settings=settings,
    )
    assert any("0 tools" in hint for hint in hints)
    assert any("splunk_run_query" in hint for hint in hints)
    assert any("SPLUNK_CLOUD_MCP_URL" in hint for hint in hints)


@pytest.mark.asyncio
async def test_run_preflight_empty_cloud_tools() -> None:
    settings = _test_settings()
    fake_servers = [
        McpServerInfo(name="splunk_o11y", ok=True, tool_count=2, tool_names=["o11y_a", "o11y_b"]),
        McpServerInfo(name="splunk_cloud_mcp", ok=True, tool_count=0, tool_names=[]),
    ]

    with patch("mcp_load_runner.preflight.check_mcp_servers", return_value=fake_servers):
        selection = McpServerSelection(use_o11y=True, use_cloud=True)
        result = await run_preflight(
            settings,
            server_selection=selection,
            required_tools=required_tool_names(selection),
        )

    assert not result.ok
    assert "no tools" in result.message.lower()
    assert result.hints
    assert "splunk_run_query" in result.missing_tools
