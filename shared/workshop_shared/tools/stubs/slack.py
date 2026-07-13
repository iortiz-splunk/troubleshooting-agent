"""
Slack integration — see workshop_shared.slack (listener, doctor).

Enable with ENABLE_SLACK=true and run: troubleshooting-agent slack-listen
"""

from langchain_core.tools import BaseTool

from workshop_shared.config import Settings


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Slack is event-driven (slack-listen), not LangChain tools."""
    return []
