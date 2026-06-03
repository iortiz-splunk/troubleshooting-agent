"""Tool registry: aggregates tools from all integrations."""

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings
from troubleshooting_agent.tools import builtin
from troubleshooting_agent.tools.stubs import slack, splunk_mcp, splunk_o11y


def get_tools(settings: Settings) -> list[BaseTool]:
    """
    Collect all enabled tools for the agent.

    Phase 0: builtin tools only.
    Future: gated by settings.enable_* flags.
    """
    tools: list[BaseTool] = []
    tools.extend(builtin.get_tools())

    if settings.enable_splunk_o11y:
        tools.extend(splunk_o11y.get_tools(settings))
    if settings.enable_splunk_mcp:
        tools.extend(splunk_mcp.get_tools(settings))
    if settings.enable_slack:
        tools.extend(slack.get_tools(settings))

    return tools
