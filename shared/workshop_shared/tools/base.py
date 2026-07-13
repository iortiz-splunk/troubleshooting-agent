"""Tool registry: aggregates tools from all integrations."""

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from workshop_shared.config import Settings
from workshop_shared.tools import builtin

# ---------------------------------------------------------------------------
# Tool aggregation
# Built-ins always included; MCP tools passed in from McpSessionManager at runtime.
# ---------------------------------------------------------------------------


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
