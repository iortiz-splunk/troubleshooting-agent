"""Tests for Part 3 skill loader (troubleshoot entry skill)."""

from pathlib import Path

from part3_agent.skill_router import (
    ENTRY_SKILL_NAME,
    build_system_prompt,
    list_skill_names,
    load_entry_skill,
)

SKILLS_DIR = Path(__file__).resolve().parents[2] / "part3_agent" / "skills"


def test_load_entry_skill_is_troubleshoot() -> None:
    skill = load_entry_skill(skills_dir=SKILLS_DIR)
    assert skill is not None
    assert skill.name == ENTRY_SKILL_NAME
    assert "categorize" in skill.body.lower()


def test_build_system_prompt_injects_troubleshoot_only() -> None:
    base = "Base prompt."
    prompt, names, routing = build_system_prompt(
        base,
        {"rule": "error rate high"},
        "5xx errors spiking",
        skills_dir=SKILLS_DIR,
    )
    assert "Base prompt." in prompt
    assert "## Troubleshooting workflow (graph-enforced)" in prompt
    assert names == ["troubleshoot"]
    assert routing.domain_skill == "troubleshoot"
    assert routing.loaded_skills == ["troubleshoot"]
    assert routing.chars_by_skill["troubleshoot"] > 0
    assert routing.router == "graph_entry"
    assert "Workflow (mandatory order)" in prompt
    # Orchestration skill names product skills; it should not embed their full bodies.
    assert "## Recommended Workflow" not in prompt


def test_list_skill_names_includes_product_skills() -> None:
    names = list_skill_names(skills_dir=SKILLS_DIR)
    assert "troubleshoot" in names
    assert "troubleshoot-apm-incidents" in names
    assert "get-alerts-or-incidents" in names
