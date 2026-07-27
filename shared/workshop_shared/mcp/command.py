"""Resolve MCP transport commands on workshop instances."""

from __future__ import annotations

import shutil
from pathlib import Path

from workshop_shared.config import Settings

_NPX_CANDIDATES = ("npx", "/usr/bin/npx", "/usr/local/bin/npx")


def resolve_mcp_npx_command(settings: Settings) -> str:
    """Return the first available npx binary for mcp-remote."""
    preferred = settings.mcp_npx_command.strip() or "npx"
    candidates = (preferred, *_NPX_CANDIDATES)
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if shutil.which(candidate):
            return shutil.which(candidate) or candidate
        path = Path(candidate)
        if path.is_file() and path.stat().st_mode & 0o111:
            return str(path)
    return preferred


def npx_availability_error(settings: Settings) -> str | None:
    """Human-readable error when Node.js/npx is missing."""
    command = resolve_mcp_npx_command(settings)
    if shutil.which(command):
        return None
    path = Path(command)
    if path.is_file() and path.stat().st_mode & 0o111:
        return None
    return (
        f"'{settings.mcp_npx_command}' was not found on PATH. "
        "Splunk MCP requires Node.js (npx). Ask your facilitator to install Node.js on this instance."
    )
