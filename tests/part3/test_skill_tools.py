"""Tests for Part 3 skill_tools."""

from pathlib import Path

from part3_agent.skill_tools import (
    SKILLS_DIR,
    list_skills,
    load_skill_content,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "part3_agent" / "skills"


def test_list_skills_returns_catalog() -> None:
    catalog = list_skills(skills_dir=FIXTURES_DIR)
    names = {item["name"] for item in catalog}
    assert "troubleshoot" in names
    assert "troubleshoot-apm-incidents" in names
    assert all("description" in item for item in catalog)


def test_load_skill_content_by_directory() -> None:
    content = load_skill_content("troubleshoot-apm-incidents", skills_dir=FIXTURES_DIR)
    assert content is not None
    assert "troubleshoot-apm-incidents" in content


def test_load_skill_content_include_reference() -> None:
    content = load_skill_content(
        "troubleshoot",
        skills_dir=FIXTURES_DIR,
        include_reference=True,
    )
    assert content is not None
    assert "reference" in content.lower()


def test_load_skill_content_unknown_returns_none() -> None:
    assert load_skill_content("nonexistent-skill", skills_dir=SKILLS_DIR) is None
