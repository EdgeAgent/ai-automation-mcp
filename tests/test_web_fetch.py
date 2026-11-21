"""Server 04 — web-fetch: extraction, failure honesty, allowlist."""

from __future__ import annotations

import pytest
from harness import initialized_client

from ai_automation_mcp.backends import FakeHttpClient
from ai_automation_mcp.demo_data import DEMO_PAGES
from ai_automation_mcp.servers import web_fetch

URL = "https://example.com/receptionist"


@pytest.fixture
def backend() -> FakeHttpClient:
    return FakeHttpClient(DEMO_PAGES)


@pytest.fixture
def client(backend: FakeHttpClient):
    return initialized_client(web_fetch.create_server(backend))


def test_fetch_extracts_readable_text(client) -> None:
    result = client.call_tool("fetch_url", {"url": URL})
    assert result["isError"] is False
    text = result["content"][0]["text"]
    assert "Never miss a call again" in text
    assert "tracking" not in text  # script content is stripped
    assert "color: red" not in text  # style content is stripped
    assert result["structuredContent"]["title"].startswith("Edge Agency")


def test_fetch_annotation_is_open_world(client) -> None:
    tool = client.list_tools()[0]
    assert tool["annotations"]["readOnlyHint"] is True
    assert tool["annotations"]["openWorldHint"] is True


def test_failed_fetch_is_an_error_not_fabricated_content(client) -> None:
    result = client.call_tool("fetch_url", {"url": "https://example.com/missing"})
    assert result["isError"] is True
    assert "failed" in result["content"][0]["text"]


def test_non_http_url_is_refused(client) -> None:
    result = client.call_tool("fetch_url", {"url": "ftp://example.com/file"})
    assert result["isError"] is True


def test_allowlist_blocks_other_domains(backend: FakeHttpClient) -> None:
    client = initialized_client(web_fetch.create_server(backend, allowlist=["example.com"]))
    blocked = client.call_tool("fetch_url", {"url": "https://other.example.net/page"})
    assert blocked["isError"] is True
    assert "allowlist" in blocked["content"][0]["text"]
    assert backend.requested == []  # blocked before any fetch happened


def test_allowlist_permits_listed_domain(backend: FakeHttpClient) -> None:
    client = initialized_client(web_fetch.create_server(backend, allowlist=["example.com"]))
    result = client.call_tool("fetch_url", {"url": URL})
    assert result["isError"] is False


def test_policy_resource_reflects_allowlist(backend: FakeHttpClient) -> None:
    client = initialized_client(web_fetch.create_server(backend, allowlist=["example.com"]))
    policy = client.read_resource("docs://fetch-policy")
    assert "example.com" in policy
    assert "never fabricates" in policy
