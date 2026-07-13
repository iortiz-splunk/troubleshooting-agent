"""Part 2 agent: Part 1 runtime with extended prompt (skills wired manually in workshop)."""

from part1_agent.agent import run_chat as _part1_run_chat
from part2_agent.prompt import SYSTEM_PROMPT
from workshop_shared.config import Settings

__all__ = ["run_chat", "SYSTEM_PROMPT"]


def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    return _part1_run_chat(
        settings,
        user_message,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=investigation_metadata,
        system_prompt=SYSTEM_PROMPT,
    )
