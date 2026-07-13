"""
Splunk Cloud MCP server integration (platform / logs).

Uses Authorization Bearer and splunk_tenant — not Observability-only auth.
Enable with ENABLE_SPLUNK_CLOUD_MCP=true.
"""

from langchain_core.tools import BaseTool
from mcp import ClientSession

from workshop_shared.config import Settings
from workshop_shared.mcp.bridge import create_langchain_tools_from_session


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Sync registry hook — tools are injected by McpSessionManager."""
    return []


async def load_tools(session: ClientSession, settings: Settings) -> list[BaseTool]:
    """Load Splunk Cloud MCP tools (no o11y_ prefix filter)."""
    _ = settings
    return await create_langchain_tools_from_session(session)
