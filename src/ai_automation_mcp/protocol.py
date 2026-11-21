"""JSON-RPC 2.0 and MCP protocol constants.

The Model Context Protocol is JSON-RPC 2.0 with a small set of methods:
an ``initialize`` handshake, ``tools/list`` + ``tools/call``,
``resources/list`` + ``resources/read``, ``prompts/list`` + ``prompts/get``,
and ``ping``. This module holds the wire-level pieces the server core
needs — nothing here knows about any individual server's tools.
"""

from __future__ import annotations

# Protocol versions this implementation can speak. The server negotiates:
# it echoes the client's requested version when supported and otherwise
# answers with the newest version it knows.
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]

# JSON-RPC 2.0 error codes, plus the MCP server-not-initialized code.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_NOT_INITIALIZED = -32002
RESOURCE_NOT_FOUND = -32002


class ToolError(Exception):
    """A tool-level failure.

    Per the MCP spec, errors from a tool's own logic are reported inside
    the ``tools/call`` result with ``isError: true`` — they are not
    JSON-RPC protocol errors. Handlers raise this (or any exception) and
    the server core converts it.
    """
