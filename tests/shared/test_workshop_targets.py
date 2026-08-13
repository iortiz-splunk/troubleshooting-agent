"""Tests for workshop O11y environment and Splunk index resolution."""

from workshop_shared.config import Settings
from workshop_shared.workshop_targets import (
    append_workshop_targets_prompt,
    resolve_o11y_environment,
    resolve_splunk_search_index,
)


def test_settings_default_workshop_targets() -> None:
    settings = Settings()
    assert settings.splunk_o11y_environment == "sre-agent-workshop"
    assert settings.splunk_search_index == "splunk4rookies-workshop"


def test_resolve_o11y_environment_prefers_alert() -> None:
    settings = Settings(splunk_o11y_environment="custom-env")
    environment = resolve_o11y_environment(
        settings=settings,
        alert={"sf_environment": "Brian-E-AD-Capital"},
        investigation_metadata={"environment": "ignored"},
    )
    assert environment == "Brian-E-AD-Capital"


def test_resolve_o11y_environment_falls_back_to_settings() -> None:
    settings = Settings(splunk_o11y_environment="my-prod")
    environment = resolve_o11y_environment(
        settings=settings,
        alert=None,
        investigation_metadata={},
    )
    assert environment == "my-prod"


def test_resolve_splunk_search_index_uses_settings() -> None:
    settings = Settings(splunk_search_index="my-app-logs")
    index = resolve_splunk_search_index(settings=settings, catalog=None)
    assert index == "my-app-logs"


def test_append_workshop_targets_prompt_includes_values() -> None:
    settings = Settings(
        splunk_o11y_environment="staging",
        splunk_search_index="k8s-apps",
    )
    prompt = append_workshop_targets_prompt("Base prompt.", settings)
    assert "staging" in prompt
    assert "k8s-apps" in prompt
    assert prompt.startswith("Base prompt.")
