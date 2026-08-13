"""Normalize Splunk MCP endpoint URLs from workshop env vars."""

from __future__ import annotations

from urllib.parse import urlparse

SPLUNK_MCP_SERVER_PORT = ":8089"
SPLUNK_MCP_SERVER_PATH = "/services/mcp"


def normalize_splunk_mcp_server_url(url: str | None) -> str | None:
    """
    Ensure Splunk MCP URLs use the direct MCP server endpoint:

    ``https://<host>:8089/services/mcp``

    Workshop env vars sometimes provide only the hostname (with or without port).
    Legacy ``/system/mcp-gateway/v1/`` URLs are rewritten to the direct form using
    the same hostname. Full URLs that already include ``/services/mcp`` are unchanged.
    """
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if SPLUNK_MCP_SERVER_PATH in value.lower():
        return value

    if "/system/mcp-gateway" in value.lower():
        parsed = urlparse(value)
        if parsed.hostname:
            scheme = parsed.scheme or "https"
            return f"{scheme}://{parsed.hostname}{SPLUNK_MCP_SERVER_PORT}{SPLUNK_MCP_SERVER_PATH}"
        return value

    base = value.rstrip("/")
    if ":8089" in base.lower():
        return f"{base}{SPLUNK_MCP_SERVER_PATH}"
    return f"{base}{SPLUNK_MCP_SERVER_PORT}{SPLUNK_MCP_SERVER_PATH}"


normalize_splunk_cloud_mcp_url = normalize_splunk_mcp_server_url
normalize_splunk_o11y_gateway_url = normalize_splunk_mcp_server_url
normalize_splunk_enterprise_mcp_url = normalize_splunk_mcp_server_url
