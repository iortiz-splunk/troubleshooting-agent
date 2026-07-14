"""Load the troubleshoot orchestration skill into the Part 3 base prompt."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from part3_agent.skill_tools import (
    SKILLS_DIR,
    format_skill_for_prompt,
    list_skills,
    load_skill_content,
)

logger = logging.getLogger(__name__)

ENTRY_SKILL_NAME = "troubleshoot"


@dataclass(frozen=True)
class SkillRouting:
    """Graph entry skill load outcome for observability (terminal logs + Galileo)."""

    domain_skill: str | None
    loaded_skills: list[str]
    chars_by_skill: dict[str, int]
    router: str = "graph_entry"

    def to_metadata_json(self) -> str:
        return json.dumps(
            {
                "router": self.router,
                "domain_skill": self.domain_skill,
                "loaded_skills": self.loaded_skills,
                "scores": {},
                "chars_by_skill": self.chars_by_skill,
                "haystack_preview": "",
            },
            separators=(",", ":"),
        )


# ---------------------------------------------------------------------------
# Backward-compatible helpers (tests and docs)
# ---------------------------------------------------------------------------
def load_entry_skill(*, skills_dir: Path | None = None) -> object | None:
    """Load the main troubleshoot orchestration skill."""
    content = load_skill_content(ENTRY_SKILL_NAME, skills_dir=skills_dir or SKILLS_DIR)
    if content is None:
        logger.warning("entry skill missing: %s", (skills_dir or SKILLS_DIR) / ENTRY_SKILL_NAME)
        return None
    from part3_agent.skill_tools import _parse_skill

    path = (skills_dir or SKILLS_DIR) / ENTRY_SKILL_NAME / "SKILL.md"
    return _parse_skill(path)


def list_skill_names(*, skills_dir: Path | None = None) -> list[str]:
    """Return names of all skills on disk (for docs/tests)."""
    return [item["name"] for item in list_skills(skills_dir=skills_dir)]


# ---------------------------------------------------------------------------
# Prompt assembly
# Base Part 3 prompt; graph nodes load product skills programmatically.
# ---------------------------------------------------------------------------
def build_system_prompt(
    base: str,
    metadata: dict[str, str] | None = None,
    alert_text: str = "",
    *,
    skills_dir: Path | None = None,
) -> tuple[str, list[str], SkillRouting]:
    """Append a minimal troubleshoot overview; full workflow is enforced by the graph."""
    _ = metadata, alert_text
    chunk = format_skill_for_prompt(ENTRY_SKILL_NAME, skills_dir=skills_dir)
    if not chunk:
        routing = SkillRouting(
            domain_skill=None,
            loaded_skills=[],
            chars_by_skill={},
        )
        return base, [], routing

    prompt = (
        f"{base}\n\n## Troubleshooting workflow (graph-enforced)\n\n"
        "The runtime graph runs: identify → categorize → investigate → report.\n"
        "Product playbooks are loaded automatically per step.\n\n"
        f"{chunk}"
    )
    logger.info("skill_router loaded skill=%s", ENTRY_SKILL_NAME)
    routing = SkillRouting(
        domain_skill=ENTRY_SKILL_NAME,
        loaded_skills=[ENTRY_SKILL_NAME],
        chars_by_skill={ENTRY_SKILL_NAME: len(chunk)},
    )
    return prompt, [ENTRY_SKILL_NAME], routing
