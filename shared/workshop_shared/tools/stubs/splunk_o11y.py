"""
Splunk Observability integration via Splunk Cloud MCP gateway.

Tools are loaded at agent runtime through McpSessionManager (mcp-remote + gateway URL).
Enable with ENABLE_SPLUNK_O11Y=true and set SPLUNK_O11Y_* env vars.
"""

from langchain_core.tools import BaseTool
from mcp import ClientSession

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import create_langchain_tools_from_session


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Sync registry hook — MCP o11y tools are injected by McpSessionManager in runner."""
    return []


async def load_tools(session: ClientSession, settings: Settings) -> list[BaseTool]:
    """Load Observability MCP tools (o11y_* prefix by default)."""
    return await create_langchain_tools_from_session(
        session,
        name_prefix=settings.splunk_o11y_tool_prefix or None,
    )
