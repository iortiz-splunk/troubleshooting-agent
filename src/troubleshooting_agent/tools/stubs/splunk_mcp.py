"""
Splunk MCP integration stub (Phase 2).

Will connect to the Splunk MCP server (stdio or HTTP) for log search and related
operations. Requires SPLUNK_MCP_COMMAND or equivalent launch configuration.

Enable with: ENABLE_SPLUNK_MCP=true
"""

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Return Splunk MCP tools when implemented."""
    return []
