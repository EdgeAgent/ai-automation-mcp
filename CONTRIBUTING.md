# Contributing

Thanks for helping make AI Automation MCP more useful to Python developers.

## Before opening an issue

- Check existing issues and discussions for a similar request.
- Include your Python version, operating system, the server or command
  involved, and the full error output when reporting a problem.
- For server requests, explain the job the tool does, what it must never
  do, and which backend boundary it needs.

## Development setup

Use Python 3.11 or newer, then run from the repository root:

```bash
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

## Pull request guidelines

- Keep the default install lean; the protocol core stays standard
  library only, and provider SDKs do not belong in it at all — a live
  provider is a new backend class.
- Every server follows the house rules in `docs/build-your-own-server.md`:
  one job per server, backends behind protocols, truthful annotations,
  an approval guard on anything that acts, and tests that drive the
  server through the protocol on fakes.
- Annotations are a safety surface: changing a hint needs the same
  scrutiny as changing the guard.
- Skills must pass `ai-mcp validate-skill` and follow
  `docs/build-your-own-skill.md`.
- Do not add exact version pins to `pyproject.toml`; this project
  resolves current compatible versions at installation time.
- When adding a server, register it in `servers/__init__.py`, add a
  demo factory, update the README table, and note it in the changelog.
- Run the CI commands locally and describe any trade-offs in the PR.

By submitting a contribution, you agree that it may be distributed under this project's MIT license.
