"""Injectable backends: the honest seam of every server in this repo.

A server never talks to the network or a phone provider directly. It
takes a backend implementing one of these small protocols:

- :class:`HttpClient` — one GET, HTML back. Used by Server 04.
- :class:`PhoneBackend` — place a call / send an SMS, provider-shaped.
  Used by Server 05.

Each protocol has a real adapter (httpx for HTTP) and a shipped fake.
Demos and tests wire the fakes, so the whole repository runs with zero
network and zero paid calls. Swapping in a live phone provider (Vapi,
Twilio, …) is a new class implementing :class:`PhoneBackend` — the
server, its approval guard, and its tests do not change.
"""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from ai_automation_mcp.server import JsonDict


class FetchError(Exception):
    """An HTTP fetch failed. Servers surface this; they never fake content."""


class HttpClient(Protocol):
    """Fetches a URL and returns the raw HTML body."""

    def get(self, url: str) -> str:
        """Return the response body for ``url`` or raise FetchError."""
        ...


class HttpxHttpClient:
    """The live HTTP backend (httpx, redirects followed, 20s timeout)."""

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def get(self, url: str) -> str:
        try:
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": "ai-automation-mcp/0.1 (web-fetch server)"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"GET {url} failed: {exc}") from exc
        return response.text


class FakeHttpClient:
    """Canned pages for demos and tests. Unknown URLs raise FetchError."""

    def __init__(self, pages: dict[str, str] | None = None) -> None:
        self.pages = dict(pages or {})
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        if url not in self.pages:
            raise FetchError(f"GET {url} failed: no canned page (fake client)")
        return self.pages[url]


class PhoneBackend(Protocol):
    """Provider-shaped phone operations (Vapi/Twilio-style results)."""

    def place_call(self, to: str, script: str) -> JsonDict:
        """Start an outbound call and return the provider's call record."""
        ...

    def send_sms(self, to: str, body: str) -> JsonDict:
        """Send a text message and return the provider's message record."""
        ...


class FakePhoneBackend:
    """Records what *would* happen and returns fake provider records.

    This is the only phone backend that ships in this repository. It
    cannot dial anything: the records it returns are marked ``fake`` so
    no demo output can be mistaken for a real call.
    """

    def __init__(self) -> None:
        self.calls: list[JsonDict] = []
        self.messages: list[JsonDict] = []

    def place_call(self, to: str, script: str) -> JsonDict:
        record: JsonDict = {
            "id": f"fake-call-{len(self.calls) + 1:04d}",
            "to": to,
            "status": "queued",
            "script": script,
            "fake": True,
        }
        self.calls.append(record)
        return record

    def send_sms(self, to: str, body: str) -> JsonDict:
        record: JsonDict = {
            "id": f"fake-sms-{len(self.messages) + 1:04d}",
            "to": to,
            "status": "queued",
            "body": body,
            "fake": True,
        }
        self.messages.append(record)
        return record


def backend_label(backend: Any) -> str:
    """Human label for a backend instance, used by the CLI and demo."""
    return type(backend).__name__
