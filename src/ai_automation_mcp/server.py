"""A small, correct MCP server core over stdio.

One :class:`McpServer` hosts tools, resources, and prompts and speaks
JSON-RPC 2.0 exactly the way the Model Context Protocol defines it:

- ``initialize`` negotiates the protocol version and advertises
  capabilities, ``notifications/initialized`` completes the handshake.
- ``tools/list`` / ``tools/call``, ``resources/list`` /
  ``resources/read``, ``prompts/list`` / ``prompts/get``, and ``ping``
  are dispatched by :meth:`McpServer.handle_message` — the same code path
  the stdio loop uses, so tests can drive a server through the real
  protocol in-process (see ``client.py``).
- Tool definitions carry MCP *annotations* (``readOnlyHint``,
  ``destructiveHint``, ``idempotentHint``, ``openWorldHint``): the series'
  approval-gate philosophy expressed in protocol terms, so a client can
  show a human exactly which tools only read, which ones change state,
  and which ones reach the outside world before anything is called.

The protocol core is standard library only. stdout belongs to the
protocol: diagnostics go to stderr, never to stdout.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TextIO

from ai_automation_mcp import __version__
from ai_automation_mcp.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    LATEST_PROTOCOL_VERSION,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    RESOURCE_NOT_FOUND,
    SERVER_NOT_INITIALIZED,
    SUPPORTED_PROTOCOL_VERSIONS,
    ToolError,
)

JsonDict = dict[str, Any]
ToolHandler = Callable[[JsonDict], "ToolResult"]
ResourceReader = Callable[[], str]
PromptGetter = Callable[[dict[str, str]], list[JsonDict]]


@dataclass(frozen=True)
class ToolAnnotations:
    """MCP tool annotations: hints a client shows before calling a tool."""

    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False
    title: str | None = None

    def to_wire(self) -> JsonDict:
        wire: JsonDict = {
            "readOnlyHint": self.read_only,
            "destructiveHint": self.destructive,
            "idempotentHint": self.idempotent,
            "openWorldHint": self.open_world,
        }
        if self.title is not None:
            wire["title"] = self.title
        return wire


@dataclass
class ToolResult:
    """What a tool handler returns: text for the model, optional data."""

    text: str
    structured: JsonDict | None = None
    is_error: bool = False

    @classmethod
    def error(cls, message: str) -> ToolResult:
        return cls(text=message, is_error=True)

    def to_wire(self) -> JsonDict:
        wire: JsonDict = {
            "content": [{"type": "text", "text": self.text}],
            "isError": self.is_error,
        }
        if self.structured is not None:
            wire["structuredContent"] = self.structured
        return wire


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: JsonDict
    handler: ToolHandler
    annotations: ToolAnnotations = field(default_factory=ToolAnnotations)

    def to_wire(self) -> JsonDict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": self.annotations.to_wire(),
        }


@dataclass(frozen=True)
class Resource:
    uri: str
    name: str
    description: str
    reader: ResourceReader
    mime_type: str = "text/plain"

    def to_wire(self) -> JsonDict:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass(frozen=True)
class PromptArgument:
    name: str
    description: str
    required: bool = False

    def to_wire(self) -> JsonDict:
        return {
            "name": self.name,
            "description": self.description,
            "required": self.required,
        }


@dataclass(frozen=True)
class Prompt:
    name: str
    description: str
    getter: PromptGetter
    arguments: list[PromptArgument] = field(default_factory=list)

    def to_wire(self) -> JsonDict:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [argument.to_wire() for argument in self.arguments],
        }


def _result(message_id: Any, result: JsonDict) -> JsonDict:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> JsonDict:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


class McpServer:
    """An MCP server: a registry of tools/resources/prompts + dispatch."""

    def __init__(self, name: str, *, instructions: str | None = None) -> None:
        self.name = name
        self.version = __version__
        self.instructions = instructions
        self._tools: dict[str, Tool] = {}
        self._resources: dict[str, Resource] = {}
        self._prompts: dict[str, Prompt] = {}
        self._initialized = False
        self.client_info: JsonDict = {}

    # -- registration ----------------------------------------------------

    def add_tool(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def tool(
        self,
        name: str,
        description: str,
        input_schema: JsonDict,
        *,
        annotations: ToolAnnotations | None = None,
    ) -> Callable[[ToolHandler], ToolHandler]:
        """Decorator form of :meth:`add_tool`."""

        def decorator(handler: ToolHandler) -> ToolHandler:
            self.add_tool(
                Tool(
                    name=name,
                    description=description,
                    input_schema=input_schema,
                    handler=handler,
                    annotations=annotations or ToolAnnotations(),
                )
            )
            return handler

        return decorator

    def add_resource(self, resource: Resource) -> Resource:
        self._resources[resource.uri] = resource
        return resource

    def add_prompt(self, prompt: Prompt) -> Prompt:
        self._prompts[prompt.name] = prompt
        return prompt

    # -- protocol dispatch -------------------------------------------------

    def handle_message(self, message: JsonDict) -> JsonDict | None:
        """Dispatch one decoded JSON-RPC message. ``None`` = no reply."""
        method = message.get("method")
        if method is None:
            # A response to a server-initiated request; this core never
            # sends requests, so responses are simply ignored.
            return None
        params = message.get("params") or {}
        if "id" not in message:
            if method == "notifications/initialized":
                self._initialized = True
            return None  # notifications never get a response

        message_id = message["id"]
        if method == "initialize":
            return _result(message_id, self._initialize(params))
        if method == "ping":
            return _result(message_id, {})
        if not self._initialized:
            return _error(
                message_id, SERVER_NOT_INITIALIZED, "Server not initialized: send initialize first."
            )
        handler = {
            "tools/list": self._tools_list,
            "tools/call": self._tools_call,
            "resources/list": self._resources_list,
            "resources/read": self._resources_read,
            "prompts/list": self._prompts_list,
            "prompts/get": self._prompts_get,
        }.get(method)
        if handler is None:
            return _error(message_id, METHOD_NOT_FOUND, f"Method not found: {method}")
        return handler(message_id, params)

    def handle_raw(self, raw: str) -> str | None:
        """Dispatch one raw JSON line; returns the raw reply line or None."""
        try:
            message = json.loads(raw)
        except json.JSONDecodeError as exc:
            reply = _error(None, PARSE_ERROR, f"Parse error: {exc.msg}")
            return json.dumps(reply)
        if not isinstance(message, dict):
            reply = _error(None, INVALID_REQUEST, "Invalid request: expected a JSON object.")
            return json.dumps(reply)
        response = self.handle_message(message)
        return json.dumps(response) if response is not None else None

    # -- method handlers ---------------------------------------------------

    def _initialize(self, params: JsonDict) -> JsonDict:
        requested = params.get("protocolVersion", LATEST_PROTOCOL_VERSION)
        negotiated = (
            requested if requested in SUPPORTED_PROTOCOL_VERSIONS else LATEST_PROTOCOL_VERSION
        )
        self.client_info = params.get("clientInfo") or {}
        self._initialized = True
        result: JsonDict = {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": self.name, "version": self.version},
        }
        if self.instructions:
            result["instructions"] = self.instructions
        return result

    def _tools_list(self, message_id: Any, params: JsonDict) -> JsonDict:
        return _result(message_id, {"tools": [tool.to_wire() for tool in self._tools.values()]})

    def _tools_call(self, message_id: Any, params: JsonDict) -> JsonDict:
        name = params.get("name")
        tool = self._tools.get(name) if isinstance(name, str) else None
        if tool is None:
            return _error(message_id, INVALID_PARAMS, f"Unknown tool: {name!r}")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error(message_id, INVALID_PARAMS, "Tool arguments must be an object.")
        missing = [key for key in tool.input_schema.get("required", []) if key not in arguments]
        if missing:
            return _error(
                message_id,
                INVALID_PARAMS,
                f"Missing required argument(s) for {name}: {', '.join(missing)}",
            )
        try:
            result = tool.handler(arguments)
        except ToolError as exc:
            result = ToolResult.error(str(exc))
        except Exception as exc:  # noqa: BLE001 — a tool bug must not kill the server
            result = ToolResult.error(f"{type(exc).__name__}: {exc}")
        return _result(message_id, result.to_wire())

    def _resources_list(self, message_id: Any, params: JsonDict) -> JsonDict:
        resources = [resource.to_wire() for resource in self._resources.values()]
        return _result(message_id, {"resources": resources})

    def _resources_read(self, message_id: Any, params: JsonDict) -> JsonDict:
        uri = params.get("uri")
        resource = self._resources.get(uri) if isinstance(uri, str) else None
        if resource is None:
            return _error(message_id, RESOURCE_NOT_FOUND, f"Resource not found: {uri!r}")
        try:
            text = resource.reader()
        except Exception as exc:  # noqa: BLE001 — reported as a read failure, never a crash
            return _error(message_id, INTERNAL_ERROR, f"Resource read failed: {exc}")
        contents = [{"uri": resource.uri, "mimeType": resource.mime_type, "text": text}]
        return _result(message_id, {"contents": contents})

    def _prompts_list(self, message_id: Any, params: JsonDict) -> JsonDict:
        prompts = [prompt.to_wire() for prompt in self._prompts.values()]
        return _result(message_id, {"prompts": prompts})

    def _prompts_get(self, message_id: Any, params: JsonDict) -> JsonDict:
        name = params.get("name")
        prompt = self._prompts.get(name) if isinstance(name, str) else None
        if prompt is None:
            return _error(message_id, INVALID_PARAMS, f"Unknown prompt: {name!r}")
        arguments = {str(k): str(v) for k, v in (params.get("arguments") or {}).items()}
        missing = [a.name for a in prompt.arguments if a.required and a.name not in arguments]
        if missing:
            return _error(
                message_id,
                INVALID_PARAMS,
                f"Missing required prompt argument(s): {', '.join(missing)}",
            )
        try:
            messages = prompt.getter(arguments)
        except Exception as exc:  # noqa: BLE001 — reported as a prompt failure, never a crash
            return _error(message_id, INTERNAL_ERROR, f"Prompt render failed: {exc}")
        return _result(message_id, {"description": prompt.description, "messages": messages})

    # -- stdio transport -----------------------------------------------------

    def serve_stdio(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        """Run the server on stdio until EOF. Logs go to stderr only."""
        source = stdin if stdin is not None else sys.stdin
        sink = stdout if stdout is not None else sys.stdout
        print(f"{self.name} MCP server ready on stdio", file=sys.stderr)
        for line in source:
            if not line.strip():
                continue
            reply = self.handle_raw(line)
            if reply is not None:
                sink.write(reply + "\n")
                sink.flush()
