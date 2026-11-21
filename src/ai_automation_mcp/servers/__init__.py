"""The six servers, in build order, with demo and live factories.

Demo factories wire fake backends and a throwaway workspace, so the
whole set runs with zero network and zero paid calls. Live factories
wire the real seams (httpx for fetch, settings-driven paths for notes
and the CRM) — except phone-tools, for which only the fake backend
ships; see that module for why.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ai_automation_mcp.backends import FakeHttpClient, FakePhoneBackend, HttpxHttpClient
from ai_automation_mcp.config import Settings
from ai_automation_mcp.demo_data import DEMO_PAGES
from ai_automation_mcp.server import McpServer
from ai_automation_mcp.servers import (
    business_tools,
    lead_tools,
    mini_crm,
    notes_files,
    phone_tools,
    web_fetch,
)


@dataclass(frozen=True)
class ServerSpec:
    """One server in the path: what it is and how to build it."""

    number: int
    name: str
    description: str
    tools: str
    backend: str
    sends: str
    create_demo: Callable[[Path], McpServer]


def _demo_lead_tools(workdir: Path) -> McpServer:
    return lead_tools.create_server()


def _demo_business_tools(workdir: Path) -> McpServer:
    return business_tools.create_server()


def _demo_notes_files(workdir: Path) -> McpServer:
    return notes_files.create_server(workdir / "notes")


def _demo_web_fetch(workdir: Path) -> McpServer:
    return web_fetch.create_server(FakeHttpClient(DEMO_PAGES))


def _demo_phone_tools(workdir: Path) -> McpServer:
    return phone_tools.create_server(FakePhoneBackend())


def _demo_mini_crm(workdir: Path) -> McpServer:
    return mini_crm.create_server(workdir / "crm.json")


SERVERS: list[ServerSpec] = [
    ServerSpec(
        number=1,
        name="lead-tools",
        description="Check and grade a lead list before outreach (dedupe, flags, A/B/C grades).",
        tools="check_lead_list, score_lead",
        backend="none — pure local logic",
        sends="No — local only",
        create_demo=_demo_lead_tools,
    ),
    ServerSpec(
        number=2,
        name="business-tools",
        description="Deterministic quote and invoice math in exact Decimal arithmetic.",
        tools="build_quote, create_invoice",
        backend="none — pure local logic",
        sends="No — documents only",
        create_demo=_demo_business_tools,
    ),
    ServerSpec(
        number=3,
        name="notes-files",
        description="Read, write, and search notes inside one sandboxed directory.",
        tools="write_note, read_note, list_notes, search_notes",
        backend="local filesystem (sandboxed)",
        sends="No — local only",
        create_demo=_demo_notes_files,
    ),
    ServerSpec(
        number=4,
        name="web-fetch",
        description="Fetch a page and return readable text; failures are errors, never faked.",
        tools="fetch_url",
        backend="injectable HTTP client",
        sends="No — reads only",
        create_demo=_demo_web_fetch,
    ),
    ServerSpec(
        number=5,
        name="phone-tools",
        description="Approval-gated call/SMS tools. Fake backend only — the guard is the lesson.",
        tools="place_call, send_sms",
        backend="FAKE backend (cannot dial)",
        sends="Gated — approved actions only, fake backend",
        create_demo=_demo_phone_tools,
    ),
    ServerSpec(
        number=6,
        name="mini-crm",
        description="A tiny local JSON CRM: add, fetch, list, and log activity on leads.",
        tools="add_lead, get_lead, list_leads, log_activity",
        backend="local JSON file",
        sends="No — local only",
        create_demo=_demo_mini_crm,
    ),
]

SERVERS_BY_NAME: dict[str, ServerSpec] = {spec.name: spec for spec in SERVERS}


def create_live_server(
    name: str,
    settings: Settings,
    *,
    notes_dir: Path | None = None,
    crm_path: Path | None = None,
    allowlist: list[str] | None = None,
) -> McpServer:
    """Build a server for a real stdio run (``ai-mcp run``)."""
    if name == "lead-tools":
        return lead_tools.create_server()
    if name == "business-tools":
        return business_tools.create_server()
    if name == "notes-files":
        return notes_files.create_server(notes_dir or settings.notes_dir)
    if name == "web-fetch":
        domains = allowlist if allowlist is not None else (settings.allowlist or None)
        return web_fetch.create_server(HttpxHttpClient(), allowlist=domains)
    if name == "phone-tools":
        print(
            "phone-tools: FAKE BACKEND — this build cannot dial or text anyone. "
            "Calls and messages are recorded as fake records only.",
            file=sys.stderr,
        )
        return phone_tools.create_server(FakePhoneBackend())
    if name == "mini-crm":
        return mini_crm.create_server(crm_path or settings.crm_path)
    raise ValueError(f"Unknown server: {name}")
