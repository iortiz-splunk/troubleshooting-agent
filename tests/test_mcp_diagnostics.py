"""Tests for MCP doctor diagnostics."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import StdioServerParameters

from workshop_shared.config import Settings
from workshop_shared.mcp.diagnostics import (
    build_server_context_hints,
    capture_mcp_remote_stderr,
    extract_mcp_remote_url,
    format_mcp_remote_command,
    hints_for_mcp_error,
)


def test_extract_mcp_remote_url() -> None:
    args = ["-y", "mcp-remote", "https://host:8089/services/mcp", "--silent"]
    assert extract_mcp_remote_url(args) == "https://host:8089/services/mcp"


def test_format_mcp_remote_command_redacts_secrets() -> None:
    params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote",
            "https://host:8089/services/mcp",
            "--silent",
            "--header",
            "X-SF-TOKEN:super-secret-token",
        ],
    )
    formatted = format_mcp_remote_command(params)
    assert "super-secret-token" not in formatted
    assert "X-SF-TOKEN: ***" in formatted


def test_hints_for_connection_closed_include_context() -> None:
    settings = Settings(
        splunk_o11y_gateway_url="https://mcp.example:8089/services/mcp",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="abc123",
        mcp_tls_insecure=True,
    )
    params = StdioServerParameters(
        command="npx",
        args=[
            "-y",
            "mcp-remote",
            settings.splunk_o11y_gateway_url or "",
            "--silent",
            "--header",
            f"X-SF-REALM:{settings.splunk_o11y_realm}",
            "--header",
            f"X-SF-TOKEN:{settings.splunk_o11y_api_token}",
        ],
    )
    hints = hints_for_mcp_error(
        "Connection closed",
        server_name="splunk_o11y",
        settings=settings,
        params=params,
    )
    assert any(h.startswith("URL:") for h in hints)
    assert any("SPLUNK_O11Y_REALM: us1" in h for h in hints)
    assert any("mcp-remote exited before" in h for h in hints)


def test_cloud_mcp_hints_flag_missing_tenant() -> None:
    settings = Settings(
        splunk_cloud_mcp_url="https://mcp.example:8089/services/mcp",
        splunk_cloud_mcp_bearer_token="jwt",
    )
    params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", settings.splunk_cloud_mcp_url or "", "--silent"],
    )
    hints = hints_for_mcp_error(
        "Connection closed",
        server_name="splunk_cloud_mcp",
        settings=settings,
        params=params,
    )
    assert any("SPLUNK_CLOUD_MCP_TENANT: missing" in h for h in hints)
    assert any("splunk_tenant header" in h for h in hints)


def test_o11y_hints_call_out_legacy_gateway_host() -> None:
    legacy_url = "https://region-pdx10.api.scs.splunk.com:8089/services/mcp"
    settings = Settings(
        splunk_o11y_gateway_url=legacy_url,
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="abc123",
        splunk_cloud_mcp_url="https://mcp-shw-abc.stg.splunkcloud.com:8089/services/mcp",
    )
    params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote", legacy_url, "--silent"],
    )
    hints = hints_for_mcp_error(
        "Connection closed",
        server_name="splunk_o11y",
        settings=settings,
        params=params,
    )
    assert any("legacy region-*.api.scs.splunk.com" in h for h in hints)
    assert any("export SPLUNK_O11Y_GATEWAY_URL=" in h for h in hints)


def test_build_server_context_hints_o11y() -> None:
    settings = Settings(
        splunk_o11y_gateway_url="https://mcp.example:8089/services/mcp",
        splunk_o11y_realm="us1",
        splunk_o11y_api_token="tok",
    )
    params = StdioServerParameters(command="npx", args=["-y", "mcp-remote", "https://mcp.example:8089/services/mcp"])
    hints = build_server_context_hints("splunk_o11y", settings, params)
    assert hints[0].startswith("URL:")


@pytest.mark.asyncio
async def test_capture_mcp_remote_stderr_timeout_returns_hint() -> None:
    params = StdioServerParameters(command="npx", args=["-y", "mcp-remote", "https://example.com:8089/services/mcp"])
    fake_proc = AsyncMock()
    fake_proc.stderr = AsyncMock()
    fake_proc.stderr.read = AsyncMock(return_value=b"")
    fake_proc.kill = MagicMock()
    fake_proc.wait = AsyncMock(return_value=0)

    async def raise_timeout(*_args: object, **_kwargs: object) -> object:
        raise asyncio.TimeoutError

    with (
        patch("workshop_shared.mcp.diagnostics.asyncio.create_subprocess_exec", return_value=fake_proc),
        patch("workshop_shared.mcp.diagnostics.asyncio.wait_for", side_effect=raise_timeout),
    ):
        message = await capture_mcp_remote_stderr(params, timeout_seconds=1.0)

    assert message is not None
    assert "did not exit" in message
    fake_proc.kill.assert_called_once()
