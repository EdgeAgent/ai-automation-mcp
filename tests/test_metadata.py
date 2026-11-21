"""Repository metadata: the docs and the package agree with each other."""

from __future__ import annotations

import tomllib
from pathlib import Path

from ai_automation_mcp import __version__
from ai_automation_mcp.servers import SERVERS

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_version_matches_pyproject() -> None:
    with open(REPO_ROOT / "pyproject.toml", "rb") as handle:
        pyproject = tomllib.load(handle)
    assert pyproject["project"]["version"] == __version__
    assert pyproject["project"]["name"] == "ai-automation-mcp"


def test_readme_names_every_server_and_skill() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for spec in SERVERS:
        assert spec.name in readme
    for skill in (
        "lead-list-checker",
        "quote-and-invoice",
        "inbox-triage",
        "phone-outreach-guardrails",
    ):
        assert skill in readme
    assert "Give your agents hands" in readme


def test_every_server_builds_a_working_demo(tmp_path: Path) -> None:
    from ai_automation_mcp.client import InProcessClient

    for spec in SERVERS:
        client = InProcessClient(spec.create_demo(tmp_path))
        result = client.initialize()
        assert result["serverInfo"]["name"] == spec.name
        assert client.list_tools(), spec.name


def test_examples_are_valid_json() -> None:
    import json

    for name in ("claude-desktop-config.json", "claude-code-config.json", "cursor-config.json"):
        data = json.loads((REPO_ROOT / "examples" / name).read_text(encoding="utf-8"))
        assert "mcpServers" in data
