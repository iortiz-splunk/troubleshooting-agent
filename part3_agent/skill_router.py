"""Load the troubleshoot orchestration skill into the Part 3 system prompt."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
ENTRY_SKILL_NAME = "troubleshoot"
MAX_SKILL_CHARS = 16_000


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str


def _parse_skill(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        return None
    meta_raw, body = match.group(1), match.group(2).strip()
    meta = yaml.safe_load(meta_raw) or {}
    if not isinstance(meta, dict):
        return None
    name = str(meta.get("name") or path.parent.name)
    description = str(meta.get("description") or "")
    return Skill(name=name, description=description, body=body)


def load_entry_skill(*, skills_dir: Path | None = None) -> Skill | None:
    """Load the main troubleshoot orchestration skill."""
    root = skills_dir or SKILLS_DIR
    path = root / ENTRY_SKILL_NAME / "SKILL.md"
    if not path.is_file():
        logger.warning("entry skill missing: %s", path)
        return None
    return _parse_skill(path)


def list_skill_names(*, skills_dir: Path | None = None) -> list[str]:
    """Return names of all skills on disk (for docs/tests)."""
    root = skills_dir or SKILLS_DIR
    if not root.is_dir():
        return []
    return sorted(p.parent.name for p in root.glob("*/SKILL.md"))


def build_system_prompt(
    base: str,
    metadata: dict[str, str] | None = None,
    alert_text: str = "",
    *,
    skills_dir: Path | None = None,
) -> tuple[str, list[str]]:
    """
    Append the troubleshoot orchestration skill to the base system prompt.

    Product-specific skills (APM, IM, RUM, etc.) are referenced by the troubleshoot
    workflow and followed by the LLM during the investigation — not pre-injected here.
    """
    _ = metadata, alert_text  # reserved for future context hints
    skill = load_entry_skill(skills_dir=skills_dir)
    if skill is None:
        return base, []

    chunk = f"### {skill.name}\n{skill.description}\n\n{skill.body}"
    if len(chunk) > MAX_SKILL_CHARS:
        chunk = chunk[: MAX_SKILL_CHARS - 20] + "\n\n...[truncated]"

    prompt = f"{base}\n\n## Active troubleshooting playbook\n\n{chunk}"
    logger.info("skill_router loaded skill=%s", skill.name)
    return prompt, [skill.name]
