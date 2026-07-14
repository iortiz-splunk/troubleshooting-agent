"""Tests for Part 2 skill injection and keyword routing."""

from pathlib import Path

import pytest

from part2_agent.skill_inject import (
    FALLBACK_SKILL,
    SKILLS_DIR,
    build_system_prompt,
    load_skill_body,
    select_skill,
)

ANSWER_SKILL_DIR = SKILLS_DIR / "error-rate"


def test_select_latency_spike() -> None:
    name = select_skill(user_message="Investigate high p99 latency on Verification")
    assert name == "latency-spike"


def test_select_latency_slow_keyword() -> None:
    name = select_skill(user_message="Why is Verification slow?")
    assert name == "latency-spike"


def test_select_error_rate_from_answer_key(tmp_path: Path) -> None:
    """Use facilitator answer file so routing works before participants finish the lab."""
    skills_root = tmp_path / "skills"
    error_dir = skills_root / "error-rate"
    error_dir.mkdir(parents=True)
    (error_dir / "SKILL.md").write_text(
        (ANSWER_SKILL_DIR / "SKILL.md.answer").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for name in ("alert-triage", "latency-spike"):
        src = SKILLS_DIR / name
        dest = skills_root / name
        dest.mkdir(parents=True)
        (dest / "SKILL.md").write_text(
            (src / "SKILL.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    name = select_skill(
        user_message="Investigate elevated 5xx errors on Verification",
        skills_dir=skills_root,
    )
    assert name == "error-rate"


def test_domain_skill_beats_triage() -> None:
    name = select_skill(
        alert_text="Incident triggered: high latency on sf_service=Verification",
        user_message="Please investigate this alert",
    )
    assert name == "latency-spike"


def test_triage_fallback_for_generic_alert() -> None:
    name = select_skill(user_message="Please triage this Observability incident")
    assert name == FALLBACK_SKILL


def test_build_system_prompt_includes_active_playbook() -> None:
    base = "Base prompt."
    prompt, loaded, routing = build_system_prompt(
        base,
        user_message="Investigate latency spike on checkout",
    )
    assert loaded == ["latency-spike", "investigation-report"]
    assert routing.domain_skill == "latency-spike"
    assert routing.loaded_skills == loaded
    assert routing.scores.get("latency-spike", 0) > 0
    assert "## Active playbook" in prompt
    assert "## Reporting requirements" in prompt
    assert "latency-spike" in prompt
    assert "investigation-report" in prompt
    assert prompt.startswith("Base prompt.")


def test_build_system_prompt_no_match_still_has_triage_fallback() -> None:
    base = "Base prompt."
    prompt, loaded, routing = build_system_prompt(base, user_message="Hello")
    assert loaded == [FALLBACK_SKILL, "investigation-report"]
    assert routing.domain_skill == FALLBACK_SKILL
    assert "alert-triage" in prompt
    assert "investigation-report" in prompt


def test_load_skill_body_truncates_large_playbook(tmp_path: Path) -> None:
    skill_dir = tmp_path / "big-skill"
    skill_dir.mkdir()
    body = "x" * 20_000
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: big-skill\ndescription: test\nalert_signals:\n  - big\n---\n\n{body}",
        encoding="utf-8",
    )
    content = load_skill_body("big-skill", skills_dir=tmp_path)
    assert content is not None
    assert len(content) <= 16_000
    assert content.endswith("...[truncated]")


def test_template_directory_is_ignored(tmp_path: Path) -> None:
    template_dir = tmp_path / "_template"
    template_dir.mkdir()
    (template_dir / "SKILL.md").write_text(
        "---\nname: should-not-load\ndescription: x\nalert_signals:\n  - should-not-load\n---\n\nbody",
        encoding="utf-8",
    )
    assert select_skill(user_message="should-not-load", skills_dir=tmp_path) is None
