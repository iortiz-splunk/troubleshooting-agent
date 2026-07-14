"""Lite keyword skill injector for Part 2 workshop (one playbook per run)."""

from __future__ import annotations

import logging
import re
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
MAX_SKILL_CHARS = 16_000
FALLBACK_SKILL = "alert-triage"
REPORT_SKILL = "investigation-report"
ROUTING_EXCLUDED = frozenset({REPORT_SKILL})


@dataclass(frozen=True)
class SkillMeta:
    name: str
    description: str
    body: str
    directory: str
    alert_signals: tuple[str, ...]


@dataclass(frozen=True)
class SkillRouting:
    """Keyword router outcome for observability (terminal logs + Galileo)."""

    domain_skill: str | None
    loaded_skills: list[str]
    scores: dict[str, int]
    chars_by_skill: dict[str, int]
    haystack_preview: str

    def to_metadata_json(self) -> str:
        return json.dumps(
            {
                "router": "keyword",
                "domain_skill": self.domain_skill,
                "loaded_skills": self.loaded_skills,
                "scores": self.scores,
                "chars_by_skill": self.chars_by_skill,
                "haystack_preview": self.haystack_preview,
            },
            separators=(",", ":"),
        )


def _parse_skill(path: Path) -> SkillMeta | None:
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
    if directory.startswith("_"):
        return None
    name = str(meta.get("name") or directory)
    description = str(meta.get("description") or "")
    raw_signals = meta.get("alert_signals") or []
    signals = tuple(str(s).lower() for s in raw_signals if s)
    return SkillMeta(
        name=name,
        description=description,
        body=body,
        directory=directory,
        alert_signals=signals,
    )


def _load_all_skills(*, skills_dir: Path | None = None) -> list[SkillMeta]:
    root = skills_dir or SKILLS_DIR
    if not root.is_dir():
        return []
    skills: list[SkillMeta] = []
    for path in sorted(root.glob("*/SKILL.md")):
        skill = _parse_skill(path)
        if skill is not None:
            skills.append(skill)
    return skills


def _haystack(*parts: str) -> str:
    return "\n".join(p for p in parts if p).lower()


def _score_skill(skill: SkillMeta, haystack: str) -> int:
    return sum(1 for signal in skill.alert_signals if signal in haystack)


def _is_fallback(skill: SkillMeta) -> bool:
    return skill.name == FALLBACK_SKILL or skill.directory == FALLBACK_SKILL


def score_skills(
    alert_text: str = "",
    user_message: str = "",
    *,
    skills_dir: Path | None = None,
) -> tuple[str, dict[str, int]]:
    """Return haystack text and per-skill keyword match counts."""
    haystack = _haystack(alert_text, user_message)
    skills = _load_all_skills(skills_dir=skills_dir)
    scores: dict[str, int] = {}
    for skill in skills:
        if skill.name in ROUTING_EXCLUDED or skill.directory in ROUTING_EXCLUDED:
            continue
        scores[skill.name] = _score_skill(skill, haystack)
    return haystack, scores


def select_skill(
    alert_text: str = "",
    user_message: str = "",
    *,
    skills_dir: Path | None = None,
    scores: dict[str, int] | None = None,
) -> str | None:
    """Pick at most one skill: domain playbooks beat alert-triage fallback."""
    haystack = _haystack(alert_text, user_message)
    skills = _load_all_skills(skills_dir=skills_dir)
    if not skills:
        return None

    if scores is None:
        _, scores = score_skills(alert_text, user_message, skills_dir=skills_dir)

    domain_best: tuple[int, str] | None = None
    triage_score = scores.get(FALLBACK_SKILL, 0)
    has_triage = any(_is_fallback(skill) for skill in skills)

    for skill in skills:
        if skill.name in ROUTING_EXCLUDED or skill.directory in ROUTING_EXCLUDED:
            continue
        score = scores.get(skill.name, 0)
        if _is_fallback(skill):
            continue
        if score > 0:
            if domain_best is None or score > domain_best[0]:
                domain_best = (score, skill.name)
            elif score == domain_best[0] and skill.name < domain_best[1]:
                domain_best = (score, skill.name)

    if domain_best is not None:
        return domain_best[1]
    if triage_score > 0 and has_triage:
        return FALLBACK_SKILL
    if has_triage:
        return FALLBACK_SKILL
    return None


def load_skill_body(skill_name: str, *, skills_dir: Path | None = None) -> str | None:
    """Load formatted playbook body for prompt injection."""
    root = skills_dir or SKILLS_DIR
    path = root / skill_name / "SKILL.md"
    if not path.is_file():
        for candidate in root.glob("*/SKILL.md"):
            skill = _parse_skill(candidate)
            if skill is not None and skill.name == skill_name:
                path = candidate
                break
        else:
            return None

    skill = _parse_skill(path)
    if skill is None:
        return None

    content = f"### {skill.name}\n{skill.description}\n\n{skill.body}"
    if len(content) > MAX_SKILL_CHARS:
        content = content[: MAX_SKILL_CHARS - 20] + "\n\n...[truncated]"
    return content


def build_system_prompt(
    base: str,
    *,
    alert_text: str = "",
    user_message: str = "",
    metadata: dict[str, str] | None = None,
    skills_dir: Path | None = None,
) -> tuple[str, list[str], SkillRouting]:
    """Append domain playbook + always-on report requirements."""
    meta_text = ""
    if metadata:
        meta_text = " ".join(str(v) for v in metadata.values() if v)

    haystack, scores = score_skills(
        _haystack(alert_text, meta_text),
        user_message,
        skills_dir=skills_dir,
    )
    skill_name = select_skill(
        _haystack(alert_text, meta_text),
        user_message,
        skills_dir=skills_dir,
        scores=scores,
    )

    loaded: list[str] = []
    chars_by_skill: dict[str, int] = {}
    prompt = base
    base_len = len(prompt)

    if skill_name is not None:
        body = load_skill_body(skill_name, skills_dir=skills_dir)
        if body:
            prompt = (
                f"{prompt}\n\n## Active playbook\n\n"
                f"Follow this playbook for the current investigation (`{skill_name}`):\n\n"
                f"{body}"
            )
            loaded.append(skill_name)
            chars_by_skill[skill_name] = len(prompt) - base_len
            base_len = len(prompt)
            logger.info("skill_inject loaded skill=%s", skill_name)

    report_body = load_skill_body(REPORT_SKILL, skills_dir=skills_dir)
    if report_body:
        prompt = (
            f"{prompt}\n\n## Reporting requirements\n\n"
            f"Format your final answer using this report skill (`{REPORT_SKILL}`):\n\n"
            f"{report_body}"
        )
        loaded.append(REPORT_SKILL)
        chars_by_skill[REPORT_SKILL] = len(prompt) - base_len
        logger.info("skill_inject loaded skill=%s", REPORT_SKILL)

    routing = SkillRouting(
        domain_skill=skill_name,
        loaded_skills=loaded,
        scores=scores,
        chars_by_skill=chars_by_skill,
        haystack_preview=haystack[:500],
    )
    return prompt, loaded, routing
