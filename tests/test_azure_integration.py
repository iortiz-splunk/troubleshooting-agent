"""Optional integration tests requiring Azure OpenAI credentials."""

import os

import pytest

from troubleshooting_agent.config import Settings
from troubleshooting_agent.llm.azure import check_azure_openai_health_sync

pytestmark = pytest.mark.azure_integration


@pytest.mark.skipif(
    os.environ.get("AZURE_INTEGRATION") != "1",
    reason="Set AZURE_INTEGRATION=1 and Azure vars in .env to run",
)
def test_azure_openai_health_live() -> None:
    settings = Settings()
    if settings.llm_provider != "azure_openai":
        pytest.skip("LLM_PROVIDER must be azure_openai")
    ok, error = check_azure_openai_health_sync(settings)
    assert ok, error
