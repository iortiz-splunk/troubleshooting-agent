"""Tool registry: aggregates tools from all integrations."""

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings
from troubleshooting_agent.tools import builtin


def get_tools(
    settings: Settings,
    *,
    mcp_tools: Sequence[BaseTool] | None = None,
) -> list[BaseTool]:
    """
    Collect all enabled tools for the agent.

    Built-in tools are always included. Splunk MCP tools are passed via
    ``mcp_tools`` from McpSessionManager when ENABLE_SPLUNK_O11Y / ENABLE_SPLUNK_MCP
    are set (see agent.runner).
    """
    _ = settings
    tools: list[BaseTool] = []
    tools.extend(builtin.get_tools())
    if mcp_tools:
        tools.extend(mcp_tools)
    return tools
