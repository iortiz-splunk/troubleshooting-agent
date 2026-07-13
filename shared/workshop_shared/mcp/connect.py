"""Low-level MCP stdio connection helper."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def connect_mcp_session(
    server_params: StdioServerParameters,
) -> AsyncIterator[ClientSession]:
    """Open stdio transport and initialize an MCP client session."""
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
