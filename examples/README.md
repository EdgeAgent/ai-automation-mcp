# Client configuration examples

Every MCP host configures servers the same way at heart: a name, a
command, and arguments. Install the package first
(`python -m pip install -e .` from a clone), then adapt one of these.

| File | Host | Where it goes |
| --- | --- | --- |
| `claude-desktop-config.json` | Claude Desktop | `claude_desktop_config.json` (Settings → Developer → Edit Config) |
| `claude-code-config.json` | Claude Code | `.mcp.json` in your project root (or `claude mcp add` with the same values) |
| `cursor-config.json` | Cursor | `~/.cursor/mcp.json` (or `.cursor/mcp.json` per project) |

Notes that apply to all three:

- Each server is a separate entry: a host starts one subprocess per
  server, over stdio. Add only the servers you want the agent to have.
- `phone-tools` is included in the Claude Desktop example to show the
  full set. It ships with the **fake backend** — it cannot dial — and
  its tools refuse to run without `approved: true` in the arguments.
  Read the `phone-outreach-guardrails` skill before enabling it
  anywhere.
- `notes-files` and `mini-crm` take their paths from the `AI_MCP_*`
  environment variables shown in the examples (or the `--notes-dir` /
  `--crm-path` flags). Set them to directories you own.
- On Windows, if a host cannot start the command directly, wrap it:
  `"command": "cmd", "args": ["/c", "ai-mcp", "run", "lead-tools"]`.
