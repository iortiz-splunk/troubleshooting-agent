"""
Splunk Observability integration stub (Phase 1).

Planned tools (mirror Cursor MCP descriptors):
- o11y_search_alerts_or_incidents
- o11y_get_apm_service_errors_and_requests
- o11y_get_apm_service_latency
- o11y_get_apm_trace_tool
- o11y_execute_signalflow_program

Required env: SPLUNK_O11Y_API_TOKEN, SPLUNK_O11Y_REALM
Enable with: ENABLE_SPLUNK_O11Y=true
"""

from langchain_core.tools import BaseTool

from troubleshooting_agent.config import Settings


def get_tools(_settings: Settings) -> list[BaseTool]:
    """Return Splunk Observability tools when implemented."""
    return []
