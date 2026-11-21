# Changelog

Notable changes to AI Automation MCP are documented here.

## [0.1.0] - 2026-11-21

### Added

- A small MCP server core (`ai_automation_mcp.server`): JSON-RPC 2.0
  over stdio with the initialize handshake, tools, resources, prompts,
  and ping — standard library only, diagnostics on stderr.
- Six numbered servers in build order: lead-tools, business-tools,
  notes-files (sandboxed), web-fetch (injectable HTTP, optional
  allowlist), phone-tools (approval-gated, fake backend only), and
  mini-crm (local JSON store).
- Tool annotations on every tool (readOnly / destructive / idempotent /
  openWorld hints) — the series' approval philosophy in protocol terms.
- An in-process client harness that drives servers through the real
  protocol in tests and demos.
- A skills pack: four production-format Agent Skills
  (lead-list-checker, quote-and-invoice, inbox-triage,
  phone-outreach-guardrails), a validated skill template, and a
  `validate-skill` CLI command with its own parser/validator.
- The `ai-mcp` CLI: list servers, run any server on stdio, run the
  full fake-backend demo, validate skills. Plus `scripts/demo.py`.
- Docs: architecture (host/client/server, where approval lives,
  transports), a build-your-own-server guide ("Server 07 is yours"),
  and a build-your-own-skill guide ("Skill 05 is yours").
- Client configuration examples for Claude Desktop, Claude Code, and
  Cursor.
