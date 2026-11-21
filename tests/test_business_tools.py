"""Server 02 — business-tools, driven through the protocol."""

from __future__ import annotations

import pytest
from harness import initialized_client

from ai_automation_mcp.demo_data import SAMPLE_QUOTE_ARGUMENTS
from ai_automation_mcp.servers import business_tools


@pytest.fixture
def client():
    return initialized_client(business_tools.create_server())


def test_build_quote_totals(client) -> None:
    text = client.call_tool_text("build_quote", SAMPLE_QUOTE_ARGUMENTS)
    # Items: 400 + 2*150 = 700; tax 13% = 91.00; total 791.00.
    assert "Total: $791.00" in text
    assert "Deposit due (30%): $237.30" in text
    assert "Balance on completion: $553.70" in text


def test_build_quote_is_read_only(client) -> None:
    tools = {tool["name"]: tool for tool in client.list_tools()}
    assert tools["build_quote"]["annotations"]["readOnlyHint"] is True
    assert tools["create_invoice"]["annotations"]["readOnlyHint"] is False


def test_build_quote_decimal_exactness(client) -> None:
    result = client.call_tool(
        "build_quote",
        {
            "client": "Penny Co",
            "items": [{"description": "Widget", "quantity": 3, "unit_price": 19.99}],
            "tax_rate": 0,
        },
    )
    assert result["isError"] is False
    assert "Total: $59.97" in result["content"][0]["text"]


def test_build_quote_empty_items_is_error(client) -> None:
    result = client.call_tool("build_quote", {"client": "X", "items": []})
    assert result["isError"] is True


def test_create_invoice_numbers_and_dates(client) -> None:
    first = client.call_tool(
        "create_invoice",
        {**SAMPLE_QUOTE_ARGUMENTS, "issue_date": "2026-11-21", "due_days": 14},
    )
    invoice = first["structuredContent"]["invoice"]
    assert invoice["number"] == "INV-0001"
    assert invoice["issue_date"] == "2026-11-21"
    assert invoice["due_date"] == "2026-12-05"
    second = client.call_tool("create_invoice", SAMPLE_QUOTE_ARGUMENTS)
    assert second["structuredContent"]["invoice"]["number"] == "INV-0002"


def test_create_invoice_bad_date_is_error(client) -> None:
    result = client.call_tool(
        "create_invoice", {**SAMPLE_QUOTE_ARGUMENTS, "issue_date": "next Friday"}
    )
    assert result["isError"] is True


def test_terms_resource(client) -> None:
    text = client.read_resource("templates://invoice-terms")
    assert "due date" in text


def test_quote_request_prompt(client) -> None:
    result = client.get_prompt(
        "quote_request", {"client": "Riverside Dental", "job": "an AI receptionist"}
    )
    text = result["messages"][0]["content"]["text"]
    assert "Riverside Dental" in text
    assert "build_quote" in text
