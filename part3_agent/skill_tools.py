"""Load and list Part 3 troubleshooting skills from skills/*/SKILL.md."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
MAX_SKILL_CHARS = 16_000


# ---------------------------------------------------------------------------
# Skill model
# Parsed SKILL.md frontmatter + body from part3_agent/skills/.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    directory: str


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
    directory = path.parent.name
    name = str(meta.get("name") or directory)
    description = str(meta.get("description") or "")
    return Skill(name=name, description=description, body=body, directory=directory)


def _skill_path(skill_name: str, *, skills_dir: Path) -> Path | None:
    direct = skills_dir / skill_name / "SKILL.md"
    if direct.is_file():
        return direct
    for path in skills_dir.glob("*/SKILL.md"):
        skill = _parse_skill(path)
        if skill is not None and skill.name == skill_name:
            return path
    return None


def list_skills(*, skills_dir: Path | None = None) -> list[dict[str, str]]:
    """Return name + description catalog from YAML frontmatter."""
    root = skills_dir or SKILLS_DIR
    if not root.is_dir():
        return []
    catalog: list[dict[str, str]] = []
    for path in sorted(root.glob("*/SKILL.md")):
        skill = _parse_skill(path)
        if skill is None:
            continue
        catalog.append({"name": skill.name, "description": skill.description})
    return catalog


def load_skill_content(
    skill_name: str,
    *,
    skills_dir: Path | None = None,
    include_reference: bool = False,
) -> str | None:
    """Load full SKILL.md body for an allowlisted skill directory or name."""
    root = skills_dir or SKILLS_DIR
    path = _skill_path(skill_name, skills_dir=root)
    if path is None:
        logger.warning("skill not found: %s", skill_name)
        return None

    skill = _parse_skill(path)
    if skill is None:
        return None

    parts = [f"### {skill.name}\n{skill.description}\n\n{skill.body}"]
    if include_reference:
        ref_path = path.parent / "reference.md"
        if ref_path.is_file():
            parts.append(f"\n\n### reference\n{ref_path.read_text(encoding='utf-8').strip()}")

    content = "\n".join(parts)
    if len(content) > MAX_SKILL_CHARS:
        content = content[: MAX_SKILL_CHARS - 20] + "\n\n...[truncated]"
    return content


def format_skill_for_prompt(skill_name: str, *, skills_dir: Path | None = None) -> str:
    """Load skill content or return empty string when missing."""
    content = load_skill_content(skill_name, skills_dir=skills_dir)
    return content or ""


# ---------------------------------------------------------------------------
# LangChain tools (optional LLM use during investigate)
# ---------------------------------------------------------------------------
@tool
def list_skills_tool() -> list[dict[str, str]]:
    """List available troubleshooting playbooks (name and description)."""
    return list_skills()


@tool
def load_skill_tool(skill_name: str, include_reference: bool = False) -> str:
    """Load a troubleshooting playbook by name."""
    content = load_skill_content(skill_name, include_reference=include_reference)
    if content is None:
        return f"ERROR: skill '{skill_name}' not found"
    return content
