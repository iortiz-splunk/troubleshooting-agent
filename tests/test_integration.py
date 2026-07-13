"""Optional integration tests requiring a running Ollama instance."""

import os

import pytest

from workshop_shared.config import Settings
from workshop_shared.llm.ollama import check_ollama_health, is_configured_model_available

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("OLLAMA_INTEGRATION") != "1",
    reason="Set OLLAMA_INTEGRATION=1 to run",
)
def test_ollama_health_live() -> None:
    settings = Settings()
    ok, models, error = check_ollama_health(settings)
    assert ok, error
    assert is_configured_model_available(settings, models)
