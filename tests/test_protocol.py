"""Protocol-core tests: the wire itself, on a toy server."""

from __future__ import annotations

import pytest

from ai_automation_mcp.client import InProcessClient, McpError
from ai_automation_mcp.protocol import (
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    RESOURCE_NOT_FOUND,
    SERVER_NOT_INITIALIZED,
)
from ai_automation_mcp.server import (
    McpServer,
    Prompt,
    PromptArgument,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)


def toy_server() -> McpServer:
    server = McpServer("toy")
    server.add_tool(
        Tool(
            name="echo",
            description="Echo the message back.",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            handler=lambda args: ToolResult(text=f"echo: {args['message']}"),
            annotations=ToolAnnotations(read_only=True, idempotent=True),
        )
    )
    server.add_resource(
        Resource(
            uri="toy://readme",
            name="Toy readme",
            description="A toy resource.",
            reader=lambda: "toy resource text",
        )
    )
    server.add_prompt(
        Prompt(
            name="greet",
            description="Greet someone.",
            arguments=[PromptArgument(name="who", description="Name.", required=True)],
            getter=lambda args: [
                {"role": "user", "content": {"type": "text", "text": f"Hello, {args['who']}!"}}
            ],
        )
    )
    return server


def test_initialize_handshake() -> None:
    client = InProcessClient(toy_server())
    result = client.initialize()
    assert result["protocolVersion"] == "2025-06-18"
    assert result["serverInfo"]["name"] == "toy"
    assert set(result["capabilities"]) == {"tools", "resources", "prompts"}


def test_initialize_echoes_supported_older_version() -> None:
    client = InProcessClient(toy_server())
    result = client.initialize(protocol_version="2024-11-05")
    assert result["protocolVersion"] == "2024-11-05"


def test_initialize_falls_back_for_unknown_version() -> None:
    client = InProcessClient(toy_server())
    result = client.initialize(protocol_version="1999-01-01")
    assert result["protocolVersion"] == "2025-06-18"


def test_ping() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    assert client.ping() == {}


def test_request_before_initialize_is_refused() -> None:
    client = InProcessClient(toy_server())
    with pytest.raises(McpError) as excinfo:
        client.list_tools()
    assert excinfo.value.code == SERVER_NOT_INITIALIZED


def test_unknown_method() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    with pytest.raises(McpError) as excinfo:
        client.request("bogus/method")
    assert excinfo.value.code == METHOD_NOT_FOUND


def test_parse_error() -> None:
    server = toy_server()
    reply = server.handle_raw("{not json")
    assert reply is not None
    import json

    assert json.loads(reply)["error"]["code"] == PARSE_ERROR


def test_notification_gets_no_response() -> None:
    server = toy_server()
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.handle_message({"jsonrpc": "2.0", "method": "notifications/cancelled"}) is None


def test_tools_list_shape_and_annotations() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    tools = client.list_tools()
    assert [tool["name"] for tool in tools] == ["echo"]
    annotations = tools[0]["annotations"]
    assert annotations["readOnlyHint"] is True
    assert annotations["destructiveHint"] is False
    assert "inputSchema" in tools[0]


def test_tools_call_round_trip() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    result = client.call_tool("echo", {"message": "hands"})
    assert result["isError"] is False
    assert result["content"][0]["text"] == "echo: hands"


def test_tools_call_unknown_tool_is_invalid_params() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    with pytest.raises(McpError) as excinfo:
        client.call_tool("nope", {})
    assert excinfo.value.code == INVALID_PARAMS


def test_tools_call_missing_required_argument() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    with pytest.raises(McpError) as excinfo:
        client.call_tool("echo", {})
    assert excinfo.value.code == INVALID_PARAMS
    assert "message" in excinfo.value.message


def test_resources_list_and_read() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    resources = client.list_resources()
    assert resources[0]["uri"] == "toy://readme"
    assert client.read_resource("toy://readme") == "toy resource text"


def test_resources_read_unknown_uri() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    with pytest.raises(McpError) as excinfo:
        client.read_resource("toy://missing")
    assert excinfo.value.code == RESOURCE_NOT_FOUND


def test_prompts_list_and_get() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    prompts = client.list_prompts()
    assert prompts[0]["name"] == "greet"
    result = client.get_prompt("greet", {"who": "Ada"})
    assert result["messages"][0]["content"]["text"] == "Hello, Ada!"


def test_prompts_get_missing_required_argument() -> None:
    client = InProcessClient(toy_server())
    client.initialize()
    with pytest.raises(McpError) as excinfo:
        client.get_prompt("greet", {})
    assert excinfo.value.code == INVALID_PARAMS


def test_tool_exception_becomes_error_result_not_crash() -> None:
    server = McpServer("boom")

    def explode(args: dict) -> ToolResult:
        raise RuntimeError("kaboom")

    server.add_tool(
        Tool(name="explode", description="x", input_schema={"type": "object"}, handler=explode)
    )
    client = InProcessClient(server)
    client.initialize()
    result = client.call_tool("explode")
    assert result["isError"] is True
    assert "kaboom" in result["content"][0]["text"]
    # The server is still alive afterwards.
    assert client.ping() == {}
