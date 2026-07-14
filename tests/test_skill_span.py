"""Tests for skill-load child span helper."""

from __future__ import annotations

import pytest
from langchain_core.runnables import RunnableConfig

from workshop_shared.observability.skill_span import emit_skill_load


@pytest.mark.asyncio
async def test_emit_skill_load_returns_skill_payload() -> None:
    parent = RunnableConfig(metadata={"agent.node": "categorize"})
    result = await emit_skill_load(
        parent,
        skill_name="troubleshoot-apm-incidents",
        role="route",
        chars=1800,
        detail="product_type=apm",
    )

    assert result["skill"] == "troubleshoot-apm-incidents"
    assert result["role"] == "route"
    assert result["chars_injected"] == 1800
    assert result["detail"] == "product_type=apm"
