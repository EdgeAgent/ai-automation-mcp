"""Server 05 — phone-tools: the approval guard is the test."""

from __future__ import annotations

import pytest
from harness import initialized_client

from ai_automation_mcp.backends import FakePhoneBackend
from ai_automation_mcp.servers import phone_tools

CALL = {"to": "+13135550142", "script": "Hello, this is Edge Agency calling about your listing."}
SMS = {"to": "+13135550142", "body": "Your free sample pack is ready."}


@pytest.fixture
def backend() -> FakePhoneBackend:
    return FakePhoneBackend()


@pytest.fixture
def client(backend: FakePhoneBackend):
    return initialized_client(phone_tools.create_server(backend))


def test_tools_are_annotated_destructive_and_open_world(client) -> None:
    for tool in client.list_tools():
        annotations = tool["annotations"]
        assert annotations["destructiveHint"] is True
        assert annotations["openWorldHint"] is True
        assert annotations["readOnlyHint"] is False


def test_call_without_approval_never_touches_backend(client, backend: FakePhoneBackend) -> None:
    result = client.call_tool("place_call", CALL)
    assert result["isError"] is True
    assert "Approval required" in result["content"][0]["text"]
    assert backend.calls == []


def test_call_with_approval_false_never_touches_backend(client, backend: FakePhoneBackend) -> None:
    result = client.call_tool("place_call", {**CALL, "approved": False})
    assert result["isError"] is True
    assert backend.calls == []


def test_call_with_approval_uses_backend_once(client, backend: FakePhoneBackend) -> None:
    result = client.call_tool("place_call", {**CALL, "approved": True})
    assert result["isError"] is False
    assert len(backend.calls) == 1
    record = result["structuredContent"]["call"]
    assert record["id"] == "fake-call-0001"
    assert record["fake"] is True  # the record can never pass for a real call


def test_sms_without_approval_never_touches_backend(client, backend: FakePhoneBackend) -> None:
    result = client.call_tool("send_sms", SMS)
    assert result["isError"] is True
    assert backend.messages == []


def test_sms_with_approval(client, backend: FakePhoneBackend) -> None:
    result = client.call_tool("send_sms", {**SMS, "approved": True})
    assert result["isError"] is False
    assert result["structuredContent"]["message"]["fake"] is True
    assert len(backend.messages) == 1


def test_approval_does_not_carry_over(client, backend: FakePhoneBackend) -> None:
    client.call_tool("place_call", {**CALL, "approved": True})
    second = client.call_tool("place_call", CALL)  # no approval this time
    assert second["isError"] is True
    assert len(backend.calls) == 1  # still just the approved one


def test_policy_resource(client) -> None:
    policy = client.read_resource("policy://phone-outreach")
    assert "approved: true" in policy
    assert "never-contact" in policy
