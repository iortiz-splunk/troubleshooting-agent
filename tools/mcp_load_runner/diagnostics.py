"""Logging and troubleshooting helpers for MCP load tests."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import McpServerInfo

from mcp_load_runner.servers import McpServerSelection

LOGGER_NAME = "mcp_load_runner"


class MemoryLogHandler(logging.Handler):
    """Collect formatted log lines for Streamlit display."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.lines.append(self.format(record))
        except Exception:
            self.handleError(record)


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_load_test_logging(*, level: int = logging.INFO) -> MemoryLogHandler:
    """Configure load-test logging to stderr and an in-memory buffer."""
    logger = get_logger()
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    for handler in logger.handlers:
        if isinstance(handler, MemoryLogHandler):
            handler.setFormatter(formatter)
            return handler

    memory_handler = MemoryLogHandler()
    memory_handler.setFormatter(formatter)
    logger.addHandler(memory_handler)
    return memory_handler


def _url_host(url: str | None) -> str:
    if not url:
        return "(not set)"
    parsed = urlparse(url.strip())
    if parsed.netloc:
        return parsed.netloc
    return url.strip()[:80]


def _secret_status(value: str | None) -> str:
    if not value or not value.strip():
        return "missing"
    return f"set ({len(value.strip())} chars)"


def summarize_settings(settings: Settings, *, env_file: str | None = None) -> list[str]:
    """Non-secret configuration summary for troubleshooting."""
    lines = [
        f"Env file: {env_file or '(default Settings() — no .env found)'}",
        f"ENABLE_SPLUNK_O11Y={settings.enable_splunk_o11y}",
    ]
    if settings.enable_splunk_o11y:
        lines.extend(
            [
                f"  SPLUNK_O11Y_GATEWAY_URL host: {_url_host(settings.splunk_o11y_gateway_url)}",
                f"  SPLUNK_O11Y_REALM: {settings.splunk_o11y_realm or '(not set)'}",
                f"  SPLUNK_O11Y_API_TOKEN: {_secret_status(settings.splunk_o11y_api_token)}",
                f"  SPLUNK_O11Y_TOOL_PREFIX: {settings.splunk_o11y_tool_prefix!r}",
            ]
        )

    lines.append(f"ENABLE_SPLUNK_CLOUD_MCP={settings.enable_splunk_cloud_mcp}")
    if settings.enable_splunk_cloud_mcp:
        lines.extend(
            [
                f"  SPLUNK_CLOUD_MCP_URL host: {_url_host(settings.splunk_cloud_mcp_url)}",
                f"  SPLUNK_CLOUD_MCP_BEARER_TOKEN: {_secret_status(settings.splunk_cloud_mcp_bearer_token)}",
                f"  SPLUNK_CLOUD_MCP_TENANT: {settings.splunk_cloud_mcp_tenant or '(not set)'}",
            ]
        )

    lines.extend(
        [
            f"MCP_NPX_COMMAND: {settings.mcp_npx_command}",
            f"MCP_ALLOW_HTTP: {settings.mcp_allow_http}",
        ]
    )
    return lines


def build_preflight_hints(
    servers: list[McpServerInfo],
    *,
    missing_tools: list[str],
    settings: Settings,
) -> list[str]:
    """Actionable hints based on preflight outcome (no secrets)."""
    hints: list[str] = []
    server_by_name = {server.name: server for server in servers}

    if not settings.enable_splunk_o11y and not settings.enable_splunk_cloud_mcp:
        hints.append(
            "Enable at least ENABLE_SPLUNK_O11Y=true and ENABLE_SPLUNK_CLOUD_MCP=true in .env."
        )

    o11y = server_by_name.get("splunk_o11y")
    if o11y and o11y.ok and o11y.tool_count == 0:
        hints.append(
            "Splunk Observability MCP connected but returned 0 tools. "
            "Check SPLUNK_O11Y_REALM, SPLUNK_O11Y_API_TOKEN, and SPLUNK_O11Y_GATEWAY_URL."
        )

    cloud = server_by_name.get("splunk_cloud_mcp")
    if cloud and cloud.ok and cloud.tool_count == 0:
        hints.extend(
            [
                "Splunk Cloud MCP connected but returned 0 tools — this is why "
                f"{', '.join(missing_tools) or 'splunk_run_query'} is missing.",
                "Confirm SPLUNK_CLOUD_MCP_URL is the direct MCP server (https://<host>:8089/services/mcp).",
                "Regenerate SPLUNK_CLOUD_MCP_BEARER_TOKEN from the Splunk MCP app install in your tenant.",
                "Set SPLUNK_CLOUD_MCP_TENANT to your Splunk Cloud tenant name (splunk_tenant header).",
                "Compare with a working Cursor MCP entry for Splunk Cloud, then run: troubleshooting-agent mcp-doctor",
            ]
        )
    elif cloud and not cloud.ok and cloud.error:
        hints.append(
            f"Splunk Cloud MCP failed to connect: {cloud.error}. "
            "Fix credentials/URL before running the load test."
        )

    if missing_tools and cloud and cloud.ok and cloud.tool_count > 0:
        hints.append(
            f"Connected servers expose {sum(s.tool_count for s in servers)} tools but not: "
            f"{', '.join(missing_tools)}. Check tool names against mcp-doctor output."
        )

    if not hints and missing_tools:
        hints.append(
            "Run troubleshooting-agent mcp-doctor and verify each required tool appears in the list."
        )

    return hints


def log_preflight_start(
    settings: Settings,
    *,
    required_tools: set[str],
    env_file: str | None,
    server_selection: McpServerSelection | None = None,
) -> None:
    logger = get_logger()
    if server_selection is not None:
        logger.info("Starting MCP preflight for: %s", server_selection.label)
    else:
        logger.info("Starting MCP preflight")
    for line in summarize_settings(settings, env_file=env_file):
        logger.info("  %s", line)
    logger.info("Required tools (%d): %s", len(required_tools), ", ".join(sorted(required_tools)))


def log_server_result(server: McpServerInfo) -> None:
    logger = get_logger()
    if server.ok:
        logger.info(
            "%s: OK — %d tool(s)%s",
            server.name,
            server.tool_count,
            f": {', '.join(server.tool_names)}" if server.tool_names else " (empty list)",
        )
        if server.tool_count == 0:
            logger.warning(
                "%s handshake succeeded but list_tools returned no tools",
                server.name,
            )
    else:
        logger.error("%s: FAILED — %s", server.name, server.error or "unknown error")


def log_preflight_outcome(*, ok: bool, message: str, hints: list[str]) -> None:
    logger = get_logger()
    if ok:
        logger.info("Preflight passed: %s", message)
        return
    logger.error("Preflight failed: %s", message)
    for hint in hints:
        logger.warning("Hint: %s", hint)
