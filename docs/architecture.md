# Architecture

How the pieces of AI Automation MCP fit together: hosts, clients,
servers, tools, backends, approval gates, and skills.

## The one-sentence version

An MCP **host** (Claude Code, Claude Desktop, Cursor, Codex, Windsurf)
runs an MCP **client** for each **server** you configure; the client and
server speak JSON-RPC 2.0, and the server exposes **tools** (actions),
**resources** (readable context), and **prompts** (reusable templates) —
while the dangerous tools sit behind an approval guard and every
external system sits behind an injectable backend.

## Who is who

```text
┌──────────────────────────────────────────────────────────────┐
│ HOST — the app the human uses (Claude Code, Cursor, …)       │
│                                                              │
│   ┌────────────┐        JSON-RPC 2.0         ┌────────────┐  │
│   │   Client   │◀─────── over stdio ────────▶│   Server   │  │
│   │ (one per   │   initialize · tools/list   │ (one job:  │  │
│   │  server)   │   tools/call · resources/…  │  lead tools│  │
│   └────────────┘   prompts/get · ping        └─────┬──────┘  │
│                                                    │         │
│   The human sees tool annotations here,            │ backend │
│   and approves (or not) before a call runs.        ▼         │
│                                          ┌────────────────┐  │
│                                          │ Backend: fake, │  │
│                                          │ httpx, your    │  │
│                                          │ provider, disk │  │
│                                          └────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

- **Host** — the application. It owns the conversation, the model, and
  the human.
- **Client** — the host's protocol speaker for one server. It launches
  the server as a subprocess (stdio) or connects to its URL (HTTP),
  runs the `initialize` handshake, and relays calls.
- **Server** — a small program with one job. It never chooses when to
  run; the client starts and stops it. All six servers here are
  instances of the shared core in `src/ai_automation_mcp/server.py`.

## The three primitives

| Primitive | Direction | In this repo |
| --- | --- | --- |
| **Tools** | The model calls them; they act or compute | `check_lead_list`, `build_quote`, `fetch_url`, `place_call`, … |
| **Resources** | The app/user reads them; they inform | the grading rubric, invoice terms, the fetch policy, the CRM summary |
| **Prompts** | The user picks them; they structure a task | `outreach_plan`, `quote_request`, `summarize_note` |

A server that is only tools is a missed opportunity: resources let a
client read the *rules* (the rubric, the policy) before trusting the
tool, and prompts encode the *routine* around the tool.

## Where approval lives

Two layers, on purpose:

1. **Annotations** (protocol layer). Every tool declares `readOnlyHint`,
   `destructiveHint`, `idempotentHint`, and `openWorldHint`. Clients
   surface these to the human *before* a call — the series' approval
   philosophy expressed in protocol terms.
2. **The guard** (server layer). Annotations are hints; a hint is not a
   lock. Server 05 (`phone-tools`) therefore enforces its rule in code:
   no `approved: true` in the arguments, no backend call. Anything you
   build that acts on the world should copy the guard, not just the
   hints. (Step 2's Recipe 06 is the same pattern as a reusable gate.)

## Backends: the honest seam

Servers never import a vendor SDK or touch the network directly. They
depend on a backend protocol (`backends.py`): `HttpClient` for fetch,
`PhoneBackend` for calls and texts. Each server ships with a fake that
makes demos and tests run with zero network and zero paid calls;
wiring a live provider is a new backend class, and the server, its
guard, and its tests do not change.

Stateful servers take their storage as a constructor argument (the
notes sandbox directory, the CRM JSON path), so tests use temp
directories and live runs use `AI_MCP_*` settings.

## Transports

- **stdio (implemented).** The client launches `ai-mcp run <server>` as
  a subprocess and speaks JSON-RPC over its stdin/stdout, one message
  per line. stdout is the protocol channel — the core writes diagnostics
  to stderr only.
- **Streamable HTTP (noted, not implemented).** The same dispatch
  (`McpServer.handle_message`) can sit behind an HTTP endpoint; the
  protocol core would not change. It is left out deliberately: six
  local servers teach the protocol better than one half-secured HTTP
  deployment, and remote MCP needs auth/session decisions that deserve
  their own step.

## Skills, briefly

Servers give agents hands; **skills** (`skills/`) teach the job: a
folder with a `SKILL.md` (frontmatter `name` + `description`, then
instructions) and bundled references. A client loads the description to
decide when the skill applies, then the instructions when it runs.
`ai_automation_mcp/skills.py` validates the format;
`docs/build-your-own-skill.md` walks through writing one.
