"""Tests for Part 3 four-node graph."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError
from part3_agent.graph import (
    _alert_mcp_params,
    _investigate_user_content,
    build_part3_graph,
)

from workshop_shared.config import Settings


class _FakeLLM(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def _agenerate(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def ainvoke(
        self, input: Any, config: RunnableConfig | None = None, **kwargs: Any
    ) -> AIMessage:
        _ = input, config, kwargs
        return AIMessage(content="Final report from report node.")


@pytest.mark.asyncio
async def test_part3_graph_runs_all_phases() -> None:
    settings = Settings()
    llm = _FakeLLM()
    apm_alert = {
        "originatingMetric": "request.latency",
        "detectLabel": "Service latency high",
        "customProperties": {"sf_service": "Verification"},
    }

    with (
        patch("part3_agent.graph.fetch_alert_payload", new_callable=AsyncMock) as mock_fetch,
        patch("part3_agent.graph.build_react_subgraph") as mock_react,
    ):
        mock_fetch.return_value = (apm_alert, None)
        mock_subgraph = MagicMock()
        mock_subgraph.compile.return_value.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="Investigation complete.")]}
        )
        mock_react.return_value = mock_subgraph

        graph = build_part3_graph(llm, [], settings=settings, base_prompt="Base.")
        app = graph.compile()
        result = await app.ainvoke(
            {
                "user_message": "troubleshoot this alert",
                "investigation_metadata": {"service": "Verification"},
                "skills_loaded": [],
            }
        )

    assert result.get("product_type") == "apm"
    assert result.get("skill_name") == "troubleshoot-apm-incidents"
    assert result.get("investigation_summary")
    assert result.get("final_report")
    assert "get-alerts-or-incidents" in (result.get("skills_loaded") or [])
    assert mock_react.call_count == 2


@pytest.mark.asyncio
async def test_react_subgraph_uses_distinct_node_names() -> None:
    settings = Settings()
    llm = _FakeLLM()
    apm_alert = {
        "originatingMetric": "request.latency",
        "customProperties": {"sf_service": "Verification"},
    }

    with (
        patch("part3_agent.graph.fetch_alert_payload", new_callable=AsyncMock) as mock_fetch,
        patch("part3_agent.graph.build_react_subgraph") as mock_react,
    ):
        mock_fetch.return_value = (apm_alert, None)
        mock_subgraph = MagicMock()
        mock_subgraph.compile.return_value.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="done")]}
        )
        mock_react.return_value = mock_subgraph

        graph = build_part3_graph(llm, [], settings=settings, base_prompt="Base.")
        app = graph.compile()
        await app.ainvoke(
            {
                "user_message": "investigate",
                "investigation_metadata": {"incident_id": "HNH10pLA0AQ"},
                "skills_loaded": [],
            }
        )

    identify_call = mock_react.call_args_list[0]
    assert identify_call.kwargs.get("llm_node_name") == "identify_llm"
    assert identify_call.kwargs.get("tools_node_name") == "identify_tools"
    investigate_call = mock_react.call_args_list[1]
    assert investigate_call.kwargs.get("llm_node_name") == "investigate_llm"
    assert investigate_call.kwargs.get("tools_node_name") == "investigate_tools"


@pytest.mark.asyncio
async def test_unknown_product_skips_investigate() -> None:
    settings = Settings()
    llm = _FakeLLM()

    with (
        patch("part3_agent.graph.fetch_alert_payload", new_callable=AsyncMock) as mock_fetch,
        patch("part3_agent.graph.build_react_subgraph") as mock_react,
    ):
        mock_fetch.return_value = (None, "not found")
        mock_subgraph = MagicMock()
        mock_subgraph.compile.return_value.ainvoke = AsyncMock(
            return_value={"messages": [AIMessage(content="could not find alert")]}
        )
        mock_react.return_value = mock_subgraph

        graph = build_part3_graph(llm, [], settings=settings, base_prompt="Base.")
        app = graph.compile()
        result = await app.ainvoke(
            {
                "user_message": "troubleshoot",
                "investigation_metadata": {},
                "skills_loaded": [],
            }
        )

    assert result.get("product_type") == "unknown"
    assert result.get("skip_investigate") is True
    assert "skipped" in (result.get("investigation_summary") or "").lower()
    assert mock_react.call_count == 1


def test_alert_mcp_params_from_alert_and_metadata() -> None:
    alert = {
        "customProperties": {"sf_service": "Verification", "sf_environment": "prod"},
    }
    params = _alert_mcp_params(alert, {"service": "ignored", "environment": "ignored"})
    assert params == {"service_name": "Verification", "environment_name": "prod"}

    params = _alert_mcp_params(None, {"service": "api", "environment": "staging"})
    assert params == {"service_name": "api", "environment_name": "staging"}


def test_investigate_user_content_includes_apm_hints() -> None:
    content = _investigate_user_content(
        user_text="investigate latency",
        alert={"sf_service": "Verification", "sf_environment": "Brian-E-AD-Capital"},
        investigation_metadata=None,
        product_type="apm",
    )
    assert "params.service_name: Verification" in content
    assert "params.environment_name: Brian-E-AD-Capital" in content
    assert "lat_buck_" in content


@pytest.mark.asyncio
async def test_investigate_recursion_limit_returns_partial_summary() -> None:
    settings = Settings()
    llm = _FakeLLM()
    apm_alert = {
        "originatingMetric": "request.latency",
        "sf_service": "Verification",
        "sf_environment": "Brian-E-AD-Capital",
    }

    with (
        patch("part3_agent.graph.fetch_alert_payload", new_callable=AsyncMock) as mock_fetch,
        patch("part3_agent.graph.build_react_subgraph") as mock_react,
    ):
        mock_fetch.return_value = (apm_alert, None)
        mock_subgraph = MagicMock()
        mock_subgraph.compile.return_value.ainvoke = AsyncMock(
            side_effect=GraphRecursionError("limit reached")
        )
        mock_react.return_value = mock_subgraph

        graph = build_part3_graph(llm, [], settings=settings, base_prompt="Base.")
        app = graph.compile()
        result = await app.ainvoke(
            {
                "user_message": "troubleshoot",
                "investigation_metadata": {"service": "Verification"},
                "skills_loaded": [],
            }
        )

    summary = result.get("investigation_summary") or ""
    assert "Investigation incomplete" in summary
    assert "lat_buck_" in summary
    assert result.get("final_report")
