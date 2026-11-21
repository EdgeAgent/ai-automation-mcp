"""Shared test helper: an initialized in-process client for a server."""

from __future__ import annotations

from ai_automation_mcp.client import InProcessClient
from ai_automation_mcp.server import McpServer


def initialized_client(server: McpServer) -> InProcessClient:
    """Return a client that has completed the initialize handshake."""
    client = InProcessClient(server)
    client.initialize()
    return client
