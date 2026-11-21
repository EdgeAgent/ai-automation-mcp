"""An in-process MCP client harness.

Tests and the demo use this client to talk to a server through the real
protocol: every message is JSON-encoded and decoded again, then handed to
:meth:`McpServer.handle_message` — the exact dispatch the stdio transport
uses. Nothing is mocked at the protocol layer; only the servers' external
backends (HTTP, phone) are faked.
"""

from __future__ import annotations

import json
from typing import Any

from ai_automation_mcp.protocol import LATEST_PROTOCOL_VERSION
from ai_automation_mcp.server import JsonDict, McpServer


class McpError(Exception):
    """A JSON-RPC error response from the server."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class InProcessClient:
    """Speaks JSON-RPC to an :class:`McpServer` living in the same process."""

    def __init__(self, server: McpServer) -> None:
        self.server = server
        self._next_id = 0

    def _send(self, message: JsonDict) -> JsonDict | None:
        # Round-trip through JSON so tests exercise the real wire format,
        # not Python object identity.
        wire = json.loads(json.dumps(message))
        response = self.server.handle_message(wire)
        return json.loads(json.dumps(response)) if response is not None else None

    def request(self, method: str, params: JsonDict | None = None) -> JsonDict:
        """Send a request and return its result; raise McpError on errors."""
        self._next_id += 1
        response = self._send(
            {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params or {}}
        )
        if response is None:
            raise McpError(0, f"No response to request {method!r}")
        if "error" in response:
            error = response["error"]
            raise McpError(int(error["code"]), str(error["message"]))
        result: JsonDict = response["result"]
        return result

    def notify(self, method: str, params: JsonDict | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    # -- the handshake ------------------------------------------------------

    def initialize(self, protocol_version: str = LATEST_PROTOCOL_VERSION) -> JsonDict:
        """Run the full handshake: initialize + notifications/initialized."""
        result = self.request(
            "initialize",
            {
                "protocolVersion": protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "ai-automation-mcp-tests", "version": "0.1.0"},
            },
        )
        self.notify("notifications/initialized")
        return result

    # -- convenience wrappers -------------------------------------------------

    def ping(self) -> JsonDict:
        return self.request("ping")

    def list_tools(self) -> list[JsonDict]:
        tools: list[JsonDict] = self.request("tools/list")["tools"]
        return tools

    def call_tool(self, name: str, arguments: JsonDict | None = None) -> JsonDict:
        """Call a tool and return the raw result (check ``isError``)."""
        return self.request("tools/call", {"name": name, "arguments": arguments or {}})

    def call_tool_text(self, name: str, arguments: JsonDict | None = None) -> str:
        """Call a tool and return its first text content block."""
        result = self.call_tool(name, arguments)
        text: str = result["content"][0]["text"]
        return text

    def list_resources(self) -> list[JsonDict]:
        resources: list[JsonDict] = self.request("resources/list")["resources"]
        return resources

    def read_resource(self, uri: str) -> str:
        result = self.request("resources/read", {"uri": uri})
        text: str = result["contents"][0]["text"]
        return text

    def list_prompts(self) -> list[JsonDict]:
        prompts: list[JsonDict] = self.request("prompts/list")["prompts"]
        return prompts

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> JsonDict:
        return self.request("prompts/get", {"name": name, "arguments": arguments or {}})
