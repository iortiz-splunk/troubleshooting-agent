"""Tests for Galileo environment wiring."""

import os

from workshop_shared.config import Settings
from workshop_shared.observability.galileo import _apply_galileo_env


def test_apply_galileo_env_overwrites_shell_placeholders() -> None:
    os.environ["GALILEO_API_KEY"] = "GALILEO_API_KEY"
    os.environ["GALILEO_CONSOLE_URL"] = "GALILEO_CONSOLE_URL"

    settings = Settings(
        enable_galileo=True,
        galileo_api_key="real-api-key",
        galileo_console_url="https://console.multitenant.galileocloud.io",
        galileo_project="ivortiz-workshop",
        galileo_log_stream="Troubleshooting-agent-workshop",
    )

    _apply_galileo_env(settings)

    assert os.environ["GALILEO_API_KEY"] == "real-api-key"
    assert os.environ["GALILEO_CONSOLE_URL"] == "https://console.multitenant.galileocloud.io"
    assert os.environ["GALILEO_PROJECT"] == "ivortiz-workshop"
    assert os.environ["GALILEO_LOG_STREAM"] == "Troubleshooting-agent-workshop"

    os.environ.pop("GALILEO_API_KEY", None)
    os.environ.pop("GALILEO_CONSOLE_URL", None)
    os.environ.pop("GALILEO_PROJECT", None)
    os.environ.pop("GALILEO_LOG_STREAM", None)
