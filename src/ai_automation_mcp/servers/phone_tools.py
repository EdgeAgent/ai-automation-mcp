"""Server 05 — phone-tools.

The dangerous end of the path, built to teach the guardrails. The tools
are shaped like a real provider API (Vapi/Twilio-style records), but two
things stand between a model and a ringing phone:

1. **The approval guard.** ``place_call`` and ``send_sms`` require
   ``approved: true`` in the tool arguments — an explicit human decision
   carried in the call itself. Without it the tool returns an error and
   the backend is *never invoked* (the tests prove the backend stays
   untouched).
2. **The annotations.** Both tools are marked destructive and
   open-world, so any MCP client can warn before the call is even made.

Only a fake backend ships in this repository: it records what would
happen and returns records marked ``fake``. Wiring a live provider
means implementing :class:`~ai_automation_mcp.backends.PhoneBackend`
with your own account — and keeping the guard.
"""

from __future__ import annotations

import json

from ai_automation_mcp.backends import PhoneBackend
from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)

POLICY = """# Phone outreach policy

- No call or text leaves this server without `approved: true` in the
  tool arguments. Approval is a human decision, recorded per action —
  there is no blanket approval.
- Scrub before outreach: check every number against your never-contact
  list and any applicable do-not-call registry *before* asking for
  approval. A number that was scrubbed out never reaches these tools.
- The approval covers one action to one number with one script/body.
  Changing any of the three needs a new approval.
- In this repository the backend is a fake that records intent and
  returns records marked `fake`. A live provider changes the backend,
  never the guard.
"""

PHONE_ANNOTATIONS = ToolAnnotations(
    read_only=False,
    destructive=True,
    idempotent=False,
    open_world=True,
)


def _require_approval(arguments: JsonDict, action: str) -> None:
    if arguments.get("approved") is not True:
        raise ToolError(
            f"Approval required: {action} needs approved=true in the tool "
            "arguments. Nothing was sent — the backend was not invoked."
        )


def create_server(backend: PhoneBackend) -> McpServer:
    """Build the phone-tools server around an injected phone backend."""
    server = McpServer(
        "phone-tools",
        instructions=(
            "Phone tools are approval-gated: approved=true is required per "
            "action, and the shipped backend is a fake that cannot dial."
        ),
    )

    def place_call(arguments: JsonDict) -> ToolResult:
        _require_approval(arguments, "place_call")
        record = backend.place_call(str(arguments["to"]), str(arguments["script"]))
        return ToolResult(
            text=f"Call {record['id']} to {record['to']}: {record['status']}.\n"
            + json.dumps(record, indent=2),
            structured={"call": record},
        )

    def send_sms(arguments: JsonDict) -> ToolResult:
        _require_approval(arguments, "send_sms")
        record = backend.send_sms(str(arguments["to"]), str(arguments["body"]))
        return ToolResult(
            text=f"SMS {record['id']} to {record['to']}: {record['status']}.\n"
            + json.dumps(record, indent=2),
            structured={"message": record},
        )

    server.add_tool(
        Tool(
            name="place_call",
            description=(
                "Place an outbound call with a script. REQUIRES approved=true "
                "in the arguments — a human approval for this exact call. "
                "Without it, nothing happens."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Phone number to call."},
                    "script": {"type": "string", "description": "What the caller says."},
                    "approved": {
                        "type": "boolean",
                        "description": "Human approval for this exact call. Default false.",
                    },
                },
                "required": ["to", "script"],
            },
            handler=place_call,
            annotations=ToolAnnotations(
                read_only=False,
                destructive=True,
                idempotent=False,
                open_world=True,
                title="Place a call (approval required)",
            ),
        )
    )
    server.add_tool(
        Tool(
            name="send_sms",
            description=(
                "Send a text message. REQUIRES approved=true in the arguments "
                "— a human approval for this exact message. Without it, "
                "nothing happens."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                    "approved": {"type": "boolean"},
                },
                "required": ["to", "body"],
            },
            handler=send_sms,
            annotations=PHONE_ANNOTATIONS,
        )
    )
    server.add_resource(
        Resource(
            uri="policy://phone-outreach",
            name="Phone outreach policy",
            description="The approval and scrub rules these tools operate under.",
            reader=lambda: POLICY,
            mime_type="text/markdown",
        )
    )
    return server
