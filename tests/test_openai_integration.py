"""Optional integration tests requiring OpenAI-compatible API credentials."""

import os

import pytest

from workshop_shared.config import Settings
from workshop_shared.llm.invoke_health import check_llm_invoke_health_sync

pytestmark = pytest.mark.openai_integration


@pytest.mark.skipif(
    os.environ.get("OPENAI_INTEGRATION") != "1",
    reason="Set OPENAI_INTEGRATION=1 and OPENAI_* vars in .env to run",
)
def test_openai_health_live() -> None:
    settings = Settings()
    if settings.llm_provider != "openai":
        pytest.skip("LLM_PROVIDER must be openai")
    ok, error = check_llm_invoke_health_sync(settings)
    assert ok, error
