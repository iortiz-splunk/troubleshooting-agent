"""Resolve MCP transport commands on workshop instances."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from workshop_shared.config import Settings

_NPX_CANDIDATES = ("npx", "/usr/bin/npx", "/usr/local/bin/npx")
_MIN_NODE_MAJOR = 18


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


def _node_binary_for_npx(npx_command: str) -> str | None:
    npx_path = shutil.which(npx_command)
    if npx_path is None:
        candidate = Path(npx_command)
        if candidate.is_file():
            npx_path = str(candidate)
        else:
            return shutil.which("node")

    node_path = Path(npx_path).with_name("node")
    if node_path.is_file():
        return str(node_path)
    return shutil.which("node")


def _node_major_version(node_command: str) -> int | None:
    try:
        completed = subprocess.run(
            [node_command, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    match = re.match(r"v?(\d+)", completed.stdout.strip())
    if not match:
        return None
    return int(match.group(1))


def npx_availability_error(settings: Settings) -> str | None:
    """Human-readable error when Node.js/npx is missing or too old for mcp-remote."""
    npx_command = resolve_mcp_npx_command(settings)
    npx_path = shutil.which(npx_command)
    if npx_path is None:
        path = Path(npx_command)
        if not (path.is_file() and path.stat().st_mode & 0o111):
            return (
                f"'{settings.mcp_npx_command}' was not found on PATH. "
                "Splunk MCP requires Node.js (npx). Ask your facilitator to install "
                "Node.js 20 on this instance."
            )

    node_command = _node_binary_for_npx(npx_command)
    if node_command is None:
        return (
            "Node.js was not found on PATH. Splunk MCP requires Node.js 18 or newer. "
            "Ask your facilitator to run scripts/workshop-instance-setup.sh on this instance."
        )

    node_major = _node_major_version(node_command)
    if node_major is None:
        return (
            "Could not determine the Node.js version. Splunk MCP requires Node.js 18 or newer. "
            "Ask your facilitator to run scripts/workshop-instance-setup.sh on this instance."
        )
    if node_major < _MIN_NODE_MAJOR:
        try:
            completed = subprocess.run(
                [node_command, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            version = completed.stdout.strip() or f"v{node_major}"
        except OSError:
            version = f"v{node_major}"
        return (
            f"Node.js {version} is too old for Splunk MCP (requires Node.js {_MIN_NODE_MAJOR}+). "
            "Ubuntu apt often installs Node 12 — ask your facilitator to upgrade to Node.js 20 "
            "with scripts/workshop-instance-setup.sh."
        )
    return None
