"""Detect workshop part and repo root from the current working directory."""

from __future__ import annotations

from pathlib import Path

PART_NAMES = ("part1_agent", "part2_agent", "part3_agent")

PART_LABELS = {
    "part1_agent": "Part 1 — minimal MCP-only agent",
    "part2_agent": "Part 2 — skills (manual wiring)",
    "part3_agent": "Part 3 — full agent + skill router",
}


class WorkshopPartError(RuntimeError):
    """Raised when troubleshooting-agent is not run from a workshop part directory."""


def find_repo_root(*, start: Path | None = None) -> Path:
    """Walk up from cwd to find the repo root (directory containing part*_agent/)."""
    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if any((path / name).is_dir() for name in PART_NAMES):
            return path
    return current


def find_env_file(*, start: Path | None = None) -> Path | None:
    """Walk up from cwd to find the nearest .env file."""
    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        candidate = path / ".env"
        if candidate.is_file():
            return candidate
    return None


def detect_workshop_part(*, start: Path | None = None, override: str | None = None) -> str:
    """
    Return part1_agent, part2_agent, or part3_agent based on cwd.

    Walks up from the current directory so subfolders of a part still work.
    """
    if override is not None:
        if override not in PART_NAMES:
            msg = f"--part must be one of: {', '.join(PART_NAMES)}"
            raise WorkshopPartError(msg)
        return override

    current = (start or Path.cwd()).resolve()
    for path in (current, *current.parents):
        if path.name in PART_NAMES:
            return path.name

    msg = (
        "Run troubleshooting-agent from inside part1_agent/, part2_agent/, or "
        f"part3_agent/ (current directory: {current}). "
        "Or pass --part part1_agent|part2_agent|part3_agent."
    )
    raise WorkshopPartError(msg)


def load_run_chat(part_name: str):
    """Import and return the run_chat entry point for a workshop part."""
    if part_name == "part1_agent":
        from part1_agent.agent import run_chat

        return run_chat
    if part_name == "part2_agent":
        from part2_agent.agent import run_chat

        return run_chat
    if part_name == "part3_agent":
        from part3_agent.agent import run_chat

        return run_chat
    msg = f"Unknown workshop part: {part_name}"
    raise WorkshopPartError(msg)
