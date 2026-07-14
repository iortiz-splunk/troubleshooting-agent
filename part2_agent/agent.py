"""Part 2 agent: Part 1 ReAct loop with lite keyword skill injection."""

from __future__ import annotations

from part1_agent.agent import run_chat as _part1_run_chat
from part2_agent.prompt import SYSTEM_PROMPT
from part2_agent.skill_inject import build_system_prompt
from workshop_shared.config import Settings

__all__ = ["run_chat", "SYSTEM_PROMPT", "build_system_prompt"]


# ---------------------------------------------------------------------------
# Part 2 entry point
# Same agent loop as Part 1; one skill playbook is injected into the system prompt.
# ---------------------------------------------------------------------------
def run_chat(
    settings: Settings,
    user_message: str,
    *,
    investigation_id: str | None = None,
    source: str = "cli",
    investigation_metadata: dict[str, str] | None = None,
) -> str:
    alert_text = user_message if source == "slack" else ""
    system_prompt, skill_names, routing = build_system_prompt(
        SYSTEM_PROMPT,
        alert_text=alert_text,
        user_message=user_message,
        metadata=investigation_metadata,
    )

    enriched_metadata = dict(investigation_metadata) if investigation_metadata else {}
    enriched_metadata["workshop_part"] = "part2_agent"
    enriched_metadata["skill_router"] = "keyword"
    if skill_names:
        enriched_metadata["skill"] = routing.domain_skill or skill_names[0]
        enriched_metadata["skills"] = ",".join(skill_names)
        enriched_metadata["skill_routing"] = routing.to_metadata_json()

    return _part1_run_chat(
        settings,
        user_message,
        investigation_id=investigation_id,
        source=source,
        investigation_metadata=enriched_metadata or None,
        system_prompt=system_prompt,
    )
