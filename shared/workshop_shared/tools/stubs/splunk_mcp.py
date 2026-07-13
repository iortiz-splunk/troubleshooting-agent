"""
Splunk Enterprise MCP integration (logs / search via Splunk MCP endpoint).

Tools are loaded at agent runtime through McpSessionManager (mcp-remote).
Enable with ENABLE_SPLUNK_MCP=true and set SPLUNK_MCP_* env vars.
"""

from langchain_core.tools import BaseTool
from mcp import ClientSession

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import create_langchain_tools_from_session


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Sync registry hook — MCP Splunk tools are injected by McpSessionManager in runner."""
    return []


async def load_tools(session: ClientSession, settings: Settings) -> list[BaseTool]:
    """Load all tools from the Splunk Enterprise MCP server."""
    _ = settings
    return await create_langchain_tools_from_session(session)
