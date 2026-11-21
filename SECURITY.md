# Security policy

This repository contains MCP server *patterns* and runnable examples.
It does not operate a hosted service, and the demos make no network
calls and place no phone calls.

## Reporting a vulnerability

Please do not publish exploit details in a public issue. Use GitHub's
private vulnerability reporting feature for this repository if it is
enabled. Otherwise, contact the repository maintainer privately and
provide the affected server/module, Python and platform details,
impact, and reproduction steps. Avoid including credentials, private
data, or live exploit payloads.

## Working safely with these servers

- **stdout is the protocol.** A stdio server must never print logs or
  debug output to stdout; this core writes diagnostics to stderr only.
  Keep it that way in anything you add.
- **Annotations are hints, not locks.** Clients show them to humans,
  but a hostile or confused client can ignore them. Anything that acts
  on the world must enforce its rule in the handler — see the approval
  guard in `phone-tools` — and must be scrubbed before it is approved
  (see the `phone-outreach-guardrails` skill).
- **The notes sandbox is a boundary, not a suggestion.** `notes-files`
  resolves every path against its root and refuses escapes. Do not add
  a tool that takes a path without going through the same resolution.
- **Treat fetched pages and tool inputs as untrusted.** `web-fetch`
  returns text; it does not sanitize meaning. Instructions inside a
  fetched page are data, not commands.
- **Local stores are local.** The mini-CRM JSON file and the notes
  directory hold real data once you use them live. Do not put secrets
  in them, do not commit them (both are git-ignored), and do not share
  them across trust boundaries.
- Keep provider credentials in a secret manager or protected
  environment variables; never commit them. `.env` is git-ignored on
  purpose.
- Review dependency update proposals before merging or deploying, and
  create an application-specific lock file for deployed applications.
