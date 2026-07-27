"""Tests for workshop env hydration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from workshop_shared.env_hydration import (
    WORKSHOP_ENV_FILES,
    _read_vars_from_login_shell,
    hydrate_workshop_env,
)


def test_read_vars_from_login_shell_parses_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 0
        stdout = "GALILEO_API_KEY=from-shell\nGALILEO_CONSOLE_URL=https://example.com\n"

    monkeypatch.setattr(
        "workshop_shared.env_hydration.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )
    values = _read_vars_from_login_shell(("GALILEO_API_KEY", "GALILEO_CONSOLE_URL"))
    assert values == {
        "GALILEO_API_KEY": "from-shell",
        "GALILEO_CONSOLE_URL": "https://example.com",
    }


def test_hydrate_workshop_env_loads_from_login_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GALILEO_API_KEY", raising=False)
    monkeypatch.delenv("GALILEO_CONSOLE_URL", raising=False)
    monkeypatch.setattr("workshop_shared.env_hydration._load_workshop_env_files", lambda: None)
    monkeypatch.setattr(
        "workshop_shared.env_hydration._read_vars_from_login_shell",
        lambda keys: {
            "GALILEO_API_KEY": "from-shell",
            "GALILEO_CONSOLE_URL": "https://example.com",
        },
    )

    hydrate_workshop_env()

    assert os.environ["GALILEO_API_KEY"] == "from-shell"
    assert os.environ["GALILEO_CONSOLE_URL"] == "https://example.com"

    os.environ.pop("GALILEO_API_KEY", None)
    os.environ.pop("GALILEO_CONSOLE_URL", None)


def test_hydrate_workshop_env_does_not_override_existing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GALILEO_API_KEY", "already-exported")
    monkeypatch.delenv("GALILEO_CONSOLE_URL", raising=False)
    monkeypatch.setattr("workshop_shared.env_hydration._load_workshop_env_files", lambda: None)
    monkeypatch.setattr(
        "workshop_shared.env_hydration._read_vars_from_login_shell",
        lambda keys: {
            "GALILEO_API_KEY": "from-shell",
            "GALILEO_CONSOLE_URL": "https://example.com",
        },
    )

    hydrate_workshop_env()

    assert os.environ["GALILEO_API_KEY"] == "already-exported"
    assert os.environ["GALILEO_CONSOLE_URL"] == "https://example.com"

    os.environ.pop("GALILEO_CONSOLE_URL", None)


def test_get_settings_uses_shell_hydration_for_galileo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "ENABLE_GALILEO=true\nGALILEO_PROJECT=workshop-test\nGALILEO_LOG_STREAM=test\n"
    )
    monkeypatch.delenv("GALILEO_API_KEY", raising=False)
    monkeypatch.delenv("GALILEO_CONSOLE_URL", raising=False)
    monkeypatch.setattr(
        "workshop_shared.env_hydration._read_vars_from_login_shell",
        lambda keys: {
            "GALILEO_API_KEY": "shell-key",
            "GALILEO_CONSOLE_URL": "https://console.example.com",
        },
    )

    from workshop_shared.config import get_settings

    settings = get_settings()
    assert settings.enable_galileo is True
    assert settings.galileo_api_key == "shell-key"
    assert settings.galileo_console_url == "https://console.example.com"

    os.environ.pop("GALILEO_API_KEY", None)
    os.environ.pop("GALILEO_CONSOLE_URL", None)


def test_workshop_env_files_are_absolute() -> None:
    for path in WORKSHOP_ENV_FILES:
        assert path.is_absolute()
