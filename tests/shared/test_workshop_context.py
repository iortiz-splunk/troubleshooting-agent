"""Tests for workshop part detection from cwd."""

from pathlib import Path

import pytest

from workshop_shared.workshop_context import (
    WorkshopPartError,
    detect_workshop_part,
    find_env_file,
    find_repo_root,
)


def test_detect_part_from_subdirectory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part_dir = tmp_path / "part2_agent" / "skills"
    part_dir.mkdir(parents=True)
    monkeypatch.chdir(part_dir)
    assert detect_workshop_part() == "part2_agent"


def test_detect_part_override() -> None:
    assert detect_workshop_part(override="part3_agent") == "part3_agent"


def test_detect_part_fails_outside_workshop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(WorkshopPartError):
        detect_workshop_part()


def test_find_repo_root(tmp_path: Path) -> None:
    (tmp_path / "part1_agent").mkdir()
    (tmp_path / "part2_agent").mkdir()
    assert find_repo_root(start=tmp_path / "part1_agent") == tmp_path


def test_find_env_file_walks_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "part1_agent").mkdir()
    (tmp_path / ".env").write_text("OLLAMA_MODEL=test\n", encoding="utf-8")
    sub = tmp_path / "part1_agent" / "skills"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    found = find_env_file()
    assert found == tmp_path / ".env"
