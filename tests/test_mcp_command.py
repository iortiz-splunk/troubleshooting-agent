"""Tests for MCP command resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from workshop_shared.config import Settings
from workshop_shared.mcp.command import npx_availability_error, resolve_mcp_npx_command


def test_resolve_mcp_npx_command_prefers_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "workshop_shared.mcp.command.shutil.which",
        lambda cmd: "/usr/bin/npx" if cmd == "npx" else None,
    )
    settings = Settings()
    assert resolve_mcp_npx_command(settings) == "/usr/bin/npx"


def test_npx_availability_error_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("workshop_shared.mcp.command.shutil.which", lambda _cmd: None)
    settings = Settings(mcp_npx_command="npx")
    error = npx_availability_error(settings)
    assert error is not None
    assert "Node.js" in error


def test_npx_availability_error_none_when_present(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    npx = tmp_path / "npx"
    npx.write_text("#!/bin/sh\n")
    npx.chmod(0o755)
    node = tmp_path / "node"
    node.write_text("#!/bin/sh\necho v20.0.0\n")
    node.chmod(0o755)
    monkeypatch.setattr(
        "workshop_shared.mcp.command.shutil.which",
        lambda cmd: str(npx) if cmd == "npx" else (str(node) if cmd == "node" else None),
    )
    monkeypatch.setattr(
        "workshop_shared.mcp.command.subprocess.run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0, "stdout": "v20.0.0\n"})(),
    )
    settings = Settings(mcp_npx_command="npx")
    assert npx_availability_error(settings) is None


def test_npx_availability_error_when_node_too_old(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "workshop_shared.mcp.command.shutil.which",
        lambda cmd: "/usr/bin/npx" if cmd == "npx" else "/usr/bin/node",
    )
    monkeypatch.setattr(
        "workshop_shared.mcp.command.subprocess.run",
        lambda *args, **kwargs: type("Completed", (), {"returncode": 0, "stdout": "v12.22.9\n"})(),
    )
    settings = Settings(mcp_npx_command="npx")
    error = npx_availability_error(settings)
    assert error is not None
    assert "too old" in error
    assert "18" in error
