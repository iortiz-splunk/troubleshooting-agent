"""
Slack integration — see troubleshooting_agent.slack (listener, doctor).

Enable with ENABLE_SLACK=true and run: troubleshoot-agent slack-listen
"""

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Slack is event-driven (slack-listen), not LangChain tools."""
    return []
