"""Tests for Part 2 skill playbooks."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "part2_agent" / "skills"


def test_part2_skill_files_exist() -> None:
    expected = ("alert-triage", "latency-spike", "error-rate")
    for name in expected:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---")
        assert "name:" in text


def test_part2_prompt_has_checklist() -> None:
    from part2_agent.prompt import SYSTEM_PROMPT

    assert "hypothesis" in SYSTEM_PROMPT.lower()
    assert "checklist" in SYSTEM_PROMPT.lower()
