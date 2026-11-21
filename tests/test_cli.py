"""The ai-mcp CLI: servers table, demo, validate-skill, version."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_automation_mcp import __version__
from ai_automation_mcp.cli import app

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_servers_table_lists_all_six() -> None:
    result = runner.invoke(app, ["servers"], env={"COLUMNS": "240"})
    assert result.exit_code == 0
    for name in (
        "lead-tools",
        "business-tools",
        "notes-files",
        "web-fetch",
        "phone-tools",
        "mini-crm",
    ):
        assert name in result.output


def test_demo_runs_and_labels_the_fake_phone_backend() -> None:
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "FAKE BACKEND" in result.output
    assert "Approval required" in result.output  # the guard refused first
    assert "fake-call-0001" in result.output
    assert "791.00" in result.output  # the quote demo's exact total


def test_validate_skill_ok_on_shipped_skill() -> None:
    result = runner.invoke(app, ["validate-skill", str(REPO_ROOT / "skills" / "inbox-triage")])
    assert result.exit_code == 0
    assert "inbox-triage" in result.output


def test_validate_skill_ok_on_template() -> None:
    result = runner.invoke(
        app, ["validate-skill", str(REPO_ROOT / "skills" / "templates" / "skill-template")]
    )
    assert result.exit_code == 0


def test_validate_skill_fails_on_broken_skill(tmp_path: Path) -> None:
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "SKILL.md").write_text("---\nname: Wrong Name\n---\n", encoding="utf-8")
    result = runner.invoke(app, ["validate-skill", str(broken)])
    assert result.exit_code == 1
    assert "INVALID" in result.output


def test_run_unknown_server_is_a_clean_error() -> None:
    result = runner.invoke(app, ["run", "nope"])
    assert result.exit_code != 0
