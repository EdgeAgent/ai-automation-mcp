"""Server 03 — notes-files: round-trips and sandbox escapes."""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import initialized_client

from ai_automation_mcp.servers import notes_files


@pytest.fixture
def client(tmp_path: Path):
    return initialized_client(notes_files.create_server(tmp_path / "notes"))


def test_write_read_round_trip(client) -> None:
    written = client.call_tool("write_note", {"name": "ideas.md", "content": "Ship Step 3."})
    assert written["isError"] is False
    assert client.call_tool_text("read_note", {"name": "ideas.md"}) == "Ship Step 3."


def test_write_is_annotated_destructive(client) -> None:
    tools = {tool["name"]: tool for tool in client.list_tools()}
    assert tools["write_note"]["annotations"]["destructiveHint"] is True
    assert tools["read_note"]["annotations"]["readOnlyHint"] is True


def test_nested_subdirectory_write(client, tmp_path: Path) -> None:
    result = client.call_tool("write_note", {"name": "projects/plan.md", "content": "Plan."})
    assert result["isError"] is False
    assert (tmp_path / "notes" / "projects" / "plan.md").is_file()


def test_list_and_search(client) -> None:
    client.call_tool("write_note", {"name": "a.md", "content": "alpha bravo"})
    client.call_tool("write_note", {"name": "b.md", "content": "charlie delta"})
    listing = client.call_tool("list_notes")
    assert listing["structuredContent"]["notes"] == ["a.md", "b.md"]
    hits = client.call_tool("search_notes", {"query": "BRAVO"})
    assert hits["structuredContent"]["matches"][0]["note"] == "a.md"
    assert "No matches" in client.call_tool_text("search_notes", {"query": "zzz"})


def test_read_missing_note_is_error(client) -> None:
    result = client.call_tool("read_note", {"name": "nope.md"})
    assert result["isError"] is True


@pytest.mark.parametrize(
    "evil_name",
    ["../escape.txt", "../../escape.txt", "sub/../../escape.txt"],
)
def test_dotdot_escape_is_refused(client, tmp_path: Path, evil_name: str) -> None:
    result = client.call_tool("write_note", {"name": evil_name, "content": "escaped"})
    assert result["isError"] is True
    assert not (tmp_path / "escape.txt").exists()
    assert not (tmp_path.parent / "escape.txt").exists()


def test_absolute_path_is_refused(client, tmp_path: Path) -> None:
    target = str(tmp_path / "abs.txt")
    result = client.call_tool("write_note", {"name": target, "content": "escaped"})
    assert result["isError"] is True
    assert not (tmp_path / "abs.txt").exists()


def test_read_escape_is_refused(client) -> None:
    result = client.call_tool("read_note", {"name": "../secret.txt"})
    assert result["isError"] is True


def test_index_resource(client) -> None:
    client.call_tool("write_note", {"name": "one.md", "content": "1"})
    assert "one.md" in client.read_resource("notes://index")


def test_summarize_prompt(client) -> None:
    result = client.get_prompt("summarize_note", {"name": "one.md"})
    assert "read_note" in result["messages"][0]["content"]["text"]
