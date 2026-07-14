"""Tests for Part 2 skill playbooks."""

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "part2_agent" / "skills"


def test_part2_skill_files_exist() -> None:
    expected = ("alert-triage", "latency-spike", "error-rate", "investigation-report")
    for name in expected:
        path = SKILLS_DIR / name / "SKILL.md"
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---")
        assert "name:" in text


def test_part2_investigation_report_forbids_raw_json() -> None:
    text = (SKILLS_DIR / "investigation-report" / "SKILL.md").read_text(encoding="utf-8")
    assert "Never" in text or "never" in text
    assert "raw" in text.lower()


def test_part2_error_rate_lab_stub_has_todos() -> None:
    text = (SKILLS_DIR / "error-rate" / "SKILL.md").read_text(encoding="utf-8")
    assert "TODO" in text


def test_part2_error_rate_answer_key_exists() -> None:
    path = SKILLS_DIR / "error-rate" / "SKILL.md.answer"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "o11y_get_apm_service_errors_and_requests" in text
    assert "5xx" in text


def test_part2_template_exists() -> None:
    path = SKILLS_DIR / "_template" / "SKILL.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "alert_signals:" in text


def test_part2_prompt_mentions_injector() -> None:
    from part2_agent.prompt import SYSTEM_PROMPT

    assert "hypothesis" in SYSTEM_PROMPT.lower()
    assert "checklist" in SYSTEM_PROMPT.lower()
    assert "auto-injected" in SYSTEM_PROMPT.lower()
