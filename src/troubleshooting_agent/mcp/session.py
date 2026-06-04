"""MCP session lifecycle for the agent run."""

from __future__ import annotations

from contextlib import AsyncExitStack
from types import TracebackType

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from troubleshooting_agent.config import Settings
from troubleshooting_agent.mcp.gateway import (
    splunk_cloud_mcp_params,
    splunk_enterprise_mcp_params,
    splunk_o11y_gateway_params,
)
from troubleshooting_agent.tools.stubs import splunk_cloud_mcp, splunk_mcp, splunk_o11y


class McpSessionManager:
    """
    Holds MCP sessions for the duration of an agent run.

    Keeps mcp-remote subprocesses alive so tool calls reuse the same connection.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._stack = AsyncExitStack()
        self._langchain_tools: list[BaseTool] = []

    async def __aenter__(self) -> McpSessionManager:
        await self._stack.__aenter__()
        if self._settings.enable_splunk_o11y:
            await self._add_o11y()
        if self._settings.enable_splunk_cloud_mcp:
            await self._add_splunk_cloud_mcp()
        if self._settings.enable_splunk_mcp:
            await self._add_splunk_enterprise_mcp()
        return self

    async def _add_o11y(self) -> None:
        params = splunk_o11y_gateway_params(self._settings)
        session = await self._open_session(params)
        tools = await splunk_o11y.load_tools(session, self._settings)
        if not tools:
            msg = (
                "Splunk Observability MCP returned no tools. "
                "Check SPLUNK_O11Y_REALM and SPLUNK_O11Y_API_TOKEN "
                "with: troubleshoot-agent mcp-doctor"
            )
            raise RuntimeError(msg)
        self._langchain_tools.extend(tools)

    async def _add_splunk_cloud_mcp(self) -> None:
        params = splunk_cloud_mcp_params(self._settings)
        session = await self._open_session(params)
        tools = await splunk_cloud_mcp.load_tools(session, self._settings)
        if not tools:
            msg = (
                "Splunk Cloud MCP returned no tools. "
                "Verify SPLUNK_CLOUD_MCP_URL, SPLUNK_CLOUD_MCP_BEARER_TOKEN, "
                "and SPLUNK_CLOUD_MCP_TENANT with: troubleshoot-agent mcp-doctor"
            )
            raise RuntimeError(msg)
        self._langchain_tools.extend(tools)

    async def _add_splunk_enterprise_mcp(self) -> None:
        params = splunk_enterprise_mcp_params(self._settings)
        session = await self._open_session(params)
        tools = await splunk_mcp.load_tools(session, self._settings)
        if not tools:
            msg = (
                "Splunk Enterprise MCP returned no tools. "
                "Verify SPLUNK_MCP_URL and SPLUNK_MCP_BEARER_TOKEN "
                "with: troubleshoot-agent mcp-doctor"
            )
            raise RuntimeError(msg)
        self._langchain_tools.extend(tools)

    async def _open_session(self, params: StdioServerParameters) -> ClientSession:
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        return session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._stack.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def langchain_tools(self) -> list[BaseTool]:
        return list(self._langchain_tools)

    @property
    def mcp_enabled(self) -> bool:
        return (
            self._settings.enable_splunk_o11y
            or self._settings.enable_splunk_cloud_mcp
            or self._settings.enable_splunk_mcp
        )
