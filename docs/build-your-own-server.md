# Build your own server — Server 07 is yours

The six servers in this repo follow one pattern. Follow the same steps
and your server gets the same guarantees: real protocol, honest
annotations, a fake-able backend, and tests that drive it the way a
client does.

## The house rules

1. **One job per server.** A server is a small program with a narrow
   brief. If the description needs "and also," split it.
2. **Backends behind protocols.** Network, providers, and disks are
   constructor-injected backends (see `backends.py`). A server that
   imports a vendor SDK directly is wired wrong.
3. **Annotations tell the truth.** Read-only tools say so; destructive
   and open-world tools say so louder. A wrong hint is a safety bug.
4. **Acting tools carry a guard.** If a tool can affect the world, an
   annotation is not enough — enforce approval in the handler, the way
   `phone-tools` refuses without `approved: true`.
5. **Errors are data, not crashes.** Tool failures return `isError`
   results with the reason; failed fetches are reported, never faked.
6. **Tests speak protocol.** Tests use the in-process client:
   initialize, `tools/list`, `tools/call`. If a test needs the network
   or money, the wiring is wrong.

## Step by step

### 1. Write the module

Create `src/ai_automation_mcp/servers/invoice_mailer.py` — and notice
how the rules bite immediately: a mailer *acts*, so it needs a backend
and a guard, exactly like `phone-tools`:

```python
"""Server 07 — invoice-mailer (example).

Sends an already-created invoice to a client. Approval-gated: the
invoice exists because Server 02 made it and a human approved it;
sending is a second, separate approval.
"""

from __future__ import annotations

from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Tool,
    ToolAnnotations,
    ToolResult,
)


def create_server(backend) -> McpServer:
    server = McpServer("invoice-mailer")

    def send_invoice(arguments: JsonDict) -> ToolResult:
        if arguments.get("approved") is not True:
            raise ToolError("Approval required: nothing was sent.")
        record = backend.send(str(arguments["to"]), str(arguments["invoice_text"]))
        return ToolResult(text=f"Sent: {record['id']}", structured={"send": record})

    server.add_tool(
        Tool(
            name="send_invoice",
            description="Email an invoice. REQUIRES approved=true.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "invoice_text": {"type": "string"},
                    "approved": {"type": "boolean"},
                },
                "required": ["to", "invoice_text"],
            },
            handler=send_invoice,
            annotations=ToolAnnotations(
                read_only=False, destructive=True, idempotent=False, open_world=True
            ),
        )
    )
    return server
```

### 2. Register it

Add a `ServerSpec` to `SERVERS` in
`src/ai_automation_mcp/servers/__init__.py` (demo factory with a fake
backend, honest "Sends anything?" answer), and a branch in
`create_live_server`.

### 3. Test it through the protocol

```python
from ai_automation_mcp.client import InProcessClient


def test_send_invoice_refuses_without_approval(fake_backend):
    client = InProcessClient(create_server(fake_backend))
    client.initialize()
    result = client.call_tool("send_invoice", {"to": "a@example.com", "invoice_text": "…"})
    assert result["isError"]
    assert fake_backend.sent == []  # the guard fired before the backend
```

### 4. Document it

Add the server to the README table (numbered, in build order), a
section in the README's server walkthrough, and a CHANGELOG entry.
If it acts on the world, the README says so in the "Sends anything?"
column — that column is a promise.

## Transports, when you need them

`ai-mcp run <server>` serves stdio. The dispatch core
(`McpServer.handle_message`) is transport-agnostic: an HTTP front end
(Streamable HTTP) is a new shell around the same core, plus the auth
and session decisions a remote server honestly requires. Read
`docs/architecture.md` before building one.
