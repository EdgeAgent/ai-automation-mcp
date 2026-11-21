"""Server 06 — mini-crm: CRUD through the protocol, plus persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import initialized_client

from ai_automation_mcp.servers import mini_crm

LEAD = {
    "name": "Dana Whitfield",
    "email": "dana@example.com",
    "phone": "(313) 555-0142",
    "company": "Whitfield Holdings",
    "source": "webinar",
}


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "crm.json"


@pytest.fixture
def client(db: Path):
    return initialized_client(mini_crm.create_server(db))


def test_add_and_get_by_id(client) -> None:
    added = client.call_tool("add_lead", LEAD)
    assert added["structuredContent"]["lead"]["id"] == "lead-0001"
    fetched = client.call_tool("get_lead", {"key": "lead-0001"})
    assert "Dana Whitfield" in fetched["content"][0]["text"]


def test_get_by_email_case_insensitive(client) -> None:
    client.call_tool("add_lead", LEAD)
    fetched = client.call_tool("get_lead", {"key": "DANA@example.com"})
    assert fetched["isError"] is False


def test_get_missing_lead_is_error(client) -> None:
    result = client.call_tool("get_lead", {"key": "lead-9999"})
    assert result["isError"] is True


def test_add_lead_needs_a_name(client) -> None:
    result = client.call_tool("add_lead", {"name": "", "email": "x@example.com"})
    assert result["isError"] is True


def test_list_leads(client) -> None:
    client.call_tool("add_lead", LEAD)
    client.call_tool("add_lead", {**LEAD, "name": "Marcus Reid", "email": "m@example.com"})
    listing = client.call_tool("list_leads")
    ids = [lead["id"] for lead in listing["structuredContent"]["leads"]]
    assert ids == ["lead-0001", "lead-0002"]


def test_log_activity_appends_history(client) -> None:
    client.call_tool("add_lead", LEAD)
    logged = client.call_tool(
        "log_activity", {"key": "lead-0001", "activity": "Sent the free sample."}
    )
    assert logged["isError"] is False
    fetched = client.call_tool("get_lead", {"key": "lead-0001"})
    assert "Sent the free sample." in fetched["content"][0]["text"]


def test_log_activity_unknown_lead_is_error(client) -> None:
    result = client.call_tool("log_activity", {"key": "lead-9999", "activity": "Hello?"})
    assert result["isError"] is True


def test_persistence_across_server_instances(db: Path) -> None:
    first = initialized_client(mini_crm.create_server(db))
    first.call_tool("add_lead", LEAD)
    second = initialized_client(mini_crm.create_server(db))
    listing = second.call_tool("list_leads")
    assert len(listing["structuredContent"]["leads"]) == 1
    added = second.call_tool("add_lead", {**LEAD, "name": "Next"})
    assert added["structuredContent"]["lead"]["id"] == "lead-0002"  # ids never reuse


def test_summary_resource(client) -> None:
    client.call_tool("add_lead", LEAD)
    assert client.read_resource("crm://summary").startswith("1 leads")
