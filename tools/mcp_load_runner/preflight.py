"""Preflight checks before MCP load tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import McpServerInfo, check_mcp_servers

from mcp_load_runner.servers import McpServerSelection, apply_server_selection
from mcp_load_runner.diagnostics import (
    build_preflight_hints,
    log_preflight_outcome,
    log_preflight_start,
    log_server_result,
)


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    servers: list[McpServerInfo]
    missing_tools: list[str]
    message: str
    hints: list[str] = field(default_factory=list)
    config_summary: list[str] = field(default_factory=list)


async def run_preflight(
    settings: Settings,
    *,
    server_selection: McpServerSelection | None = None,
    required_tools: set[str] | None = None,
    env_file: str | None = None,
) -> PreflightResult:
    selection = server_selection or McpServerSelection()
    effective_settings = apply_server_selection(settings, selection)
    required = required_tools or set()
    log_preflight_start(
        effective_settings,
        required_tools=required,
        env_file=env_file,
        server_selection=selection,
    )

    from mcp_load_runner.diagnostics import summarize_settings

    config_summary = summarize_settings(effective_settings, env_file=env_file)
    config_summary.insert(0, f"Load test MCP servers: {selection.label}")

    servers = await check_mcp_servers(effective_settings)
    for server in servers:
        log_server_result(server)

    if not servers:
        hints = build_preflight_hints(
            servers, missing_tools=sorted(required), settings=effective_settings
        )
        message = f"No MCP servers selected or enabled for: {selection.label}"
        log_preflight_outcome(ok=False, message=message, hints=hints)
        return PreflightResult(
            ok=False,
            servers=[],
            missing_tools=sorted(required),
            message=message,
            hints=hints,
            config_summary=config_summary,
        )

    failed = [server for server in servers if not server.ok]
    if failed:
        names = ", ".join(server.name for server in failed)
        message = f"MCP preflight failed for: {names}"
        hints = build_preflight_hints(
            servers, missing_tools=sorted(required), settings=effective_settings
        )
        log_preflight_outcome(ok=False, message=message, hints=hints)
        return PreflightResult(
            ok=False,
            servers=servers,
            missing_tools=sorted(required),
            message=message,
            hints=hints,
            config_summary=config_summary,
        )

    empty_tool_servers = [server for server in servers if server.ok and server.tool_count == 0]
    if empty_tool_servers:
        names = ", ".join(server.name for server in empty_tool_servers)
        message = f"MCP connected but returned no tools: {names}"
        hints = build_preflight_hints(
            servers, missing_tools=sorted(required), settings=effective_settings
        )
        log_preflight_outcome(ok=False, message=message, hints=hints)
        return PreflightResult(
            ok=False,
            servers=servers,
            missing_tools=sorted(required),
            message=message,
            hints=hints,
            config_summary=config_summary,
        )

    available_tools: set[str] = set()
    for server in servers:
        available_tools.update(server.tool_names)

    missing: list[str] = []
    if required_tools:
        missing = sorted(required_tools - available_tools)

    if missing:
        message = f"Missing required tools: {', '.join(missing)}"
        hints = build_preflight_hints(
            servers, missing_tools=missing, settings=effective_settings
        )
        log_preflight_outcome(ok=False, message=message, hints=hints)
        return PreflightResult(
            ok=False,
            servers=servers,
            missing_tools=missing,
            message=message,
            hints=hints,
            config_summary=config_summary,
        )

    message = "MCP preflight passed."
    log_preflight_outcome(ok=True, message=message, hints=[])
    return PreflightResult(
        ok=True,
        servers=servers,
        missing_tools=[],
        message=message,
        hints=[],
        config_summary=config_summary,
    )
