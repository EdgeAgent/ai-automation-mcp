"""End-to-end demo: boot all six servers on fakes, call them for real.

Every call below goes through the MCP protocol — initialize handshake,
``tools/list``, ``tools/call`` — via the in-process client. Only the
external backends are fake: the web-fetch server reads canned pages and
the phone server runs on the fake backend that cannot dial. The phone
section says so, out loud, twice: once when the approval guard refuses
an unapproved call, and once on the fake record it returns.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ai_automation_mcp.client import InProcessClient
from ai_automation_mcp.demo_data import SAMPLE_LEAD_CSV, SAMPLE_QUOTE_ARGUMENTS
from ai_automation_mcp.servers import SERVERS


def _section(title: str, body: str) -> str:
    return f"\n=== {title} ===\n{body.rstrip()}"


def run_full_demo() -> str:
    """Run every server's headline flow and return a summary report."""
    parts: list[str] = [
        "AI Automation MCP — demo on fake backends",
        (
            "Every call goes through the real MCP protocol (initialize → tools/list "
            "→ tools/call).\nZero network, zero paid calls, zero real phone calls."
        ),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        clients = {}
        for spec in SERVERS:
            client = InProcessClient(spec.create_demo(workdir))
            client.initialize()
            clients[spec.name] = client

        lead = clients["lead-tools"]
        result = lead.call_tool("check_lead_list", {"csv_text": SAMPLE_LEAD_CSV})
        stats = result["structuredContent"]["stats"]
        parts.append(
            _section(
                "01 · lead-tools — check_lead_list",
                f"{stats['input_rows']} rows in → {stats['kept_rows']} kept, "
                f"{stats['duplicates_removed']} duplicate removed. "
                f"Grades: A={stats['grade_a']} B={stats['grade_b']} C={stats['grade_c']}; "
                f"invalid emails: {stats['invalid_emails']}.",
            )
        )

        business = clients["business-tools"]
        quote_text = business.call_tool_text("build_quote", SAMPLE_QUOTE_ARGUMENTS)
        parts.append(_section("02 · business-tools — build_quote", quote_text))

        notes = clients["notes-files"]
        notes.call_tool("write_note", {"name": "demo.md", "content": "Demo note: ship Step 3."})
        found = notes.call_tool_text("search_notes", {"query": "ship"})
        parts.append(
            _section(
                "03 · notes-files — write + search",
                f"Wrote demo.md inside the sandbox; search for 'ship' → {found}",
            )
        )

        fetch = clients["web-fetch"]
        page = fetch.call_tool("fetch_url", {"url": "https://example.com/receptionist"})
        parts.append(
            _section(
                "04 · web-fetch — fetch_url (canned page, fake HTTP backend)",
                page["content"][0]["text"][:240] + "…",
            )
        )

        phone = clients["phone-tools"]
        refused = phone.call_tool(
            "place_call", {"to": "+13135550142", "script": "Hello from Edge Agency."}
        )
        approved = phone.call_tool(
            "place_call",
            {
                "to": "+13135550142",
                "script": "Hello from Edge Agency.",
                "approved": True,
            },
        )
        record = approved["structuredContent"]["call"]
        parts.append(
            _section(
                "05 · phone-tools — the approval guard (FAKE BACKEND — cannot dial)",
                f"Without approval → refused: {refused['content'][0]['text']}\n"
                f"With approval → fake record {record['id']} "
                f"(status {record['status']}, fake={record['fake']}). No real call was placed.",
            )
        )

        crm = clients["mini-crm"]
        crm.call_tool(
            "add_lead",
            {
                "name": "Dana Whitfield",
                "email": "dana@example.com",
                "phone": "(313) 555-0142",
                "company": "Whitfield Holdings",
                "source": "webinar",
            },
        )
        crm.call_tool(
            "log_activity", {"key": "lead-0001", "activity": "Sent the free sample pack."}
        )
        listing = crm.call_tool_text("list_leads")
        parts.append(_section("06 · mini-crm — add, log, list", listing))

    parts.append(
        "\nSummary: 6 servers booted, 6 handshakes, headline tools called through "
        "the protocol.\nThe phone backend was a fake throughout — nothing dialed, "
        "nothing sent, nothing charged."
    )
    return "\n".join(parts)
