"""Server 01 — lead-tools, driven through the protocol."""

from __future__ import annotations

import pytest
from harness import initialized_client

from ai_automation_mcp.client import McpError
from ai_automation_mcp.demo_data import SAMPLE_LEAD_CSV
from ai_automation_mcp.servers import lead_tools


@pytest.fixture
def client():
    return initialized_client(lead_tools.create_server())


def test_server_identity(client) -> None:
    result = client.initialize()
    assert result["serverInfo"]["name"] == "lead-tools"


def test_tools_are_read_only(client) -> None:
    for tool in client.list_tools():
        assert tool["annotations"]["readOnlyHint"] is True
        assert tool["annotations"]["openWorldHint"] is False


def test_check_lead_list_stats(client) -> None:
    result = client.call_tool("check_lead_list", {"csv_text": SAMPLE_LEAD_CSV})
    assert result["isError"] is False
    stats = result["structuredContent"]["stats"]
    assert stats["input_rows"] == 6
    assert stats["duplicates_removed"] == 1
    assert stats["kept_rows"] == 5
    assert stats["grade_a"] == 2
    assert stats["grade_b"] == 1
    assert stats["grade_c"] == 2
    assert stats["invalid_emails"] == 1


def test_check_lead_list_cleaned_csv_has_grades(client) -> None:
    result = client.call_tool("check_lead_list", {"csv_text": SAMPLE_LEAD_CSV})
    cleaned = result["structuredContent"]["cleaned_csv"]
    assert "grade" in cleaned.splitlines()[0]
    assert cleaned.count("Dana Whitfield") == 1  # duplicate gone


def test_check_lead_list_missing_argument(client) -> None:
    with pytest.raises(McpError):
        client.call_tool("check_lead_list", {})


def test_check_lead_list_headerless_csv_is_an_error_result(client) -> None:
    result = client.call_tool("check_lead_list", {"csv_text": ""})
    assert result["isError"] is True


def test_score_lead_full_contact_is_a(client) -> None:
    result = client.call_tool(
        "score_lead",
        {"name": "Dana", "email": "dana@example.com", "phone": "(313) 555-0142"},
    )
    assert result["structuredContent"]["grade"] == "A"
    assert result["structuredContent"]["flags"] == []


def test_score_lead_no_contact_is_c(client) -> None:
    result = client.call_tool("score_lead", {"name": "Sam", "email": "", "phone": ""})
    structured = result["structuredContent"]
    assert structured["grade"] == "C"
    assert "missing_email" in structured["flags"]
    assert "missing_phone" in structured["flags"]


def test_rubric_resource(client) -> None:
    text = client.read_resource("rubric://lead-grading")
    assert "A — ready" in text
    assert "C — incomplete" in text


def test_outreach_plan_prompt(client) -> None:
    result = client.get_prompt("outreach_plan", {"context": "a Detroit campaign"})
    text = result["messages"][0]["content"]["text"]
    assert "check_lead_list" in text
    assert "Detroit" in text
