"""Server 06 — mini-crm.

A tiny CRM as an MCP server: leads in a local JSON file, four tools, no
network, no account. This is the safe pattern for CRM-shaped tools —
the data lives in one file you own, every write is a tool call a client
can log, and the pattern scales up to a real CRM by swapping the store,
not the tools.

- ``add_lead`` creates a lead and returns its id (``lead-0001``, …).
- ``get_lead`` fetches by id or email; ``list_leads`` lists all.
- ``log_activity`` appends a timestamped note to a lead's history.

The store path is injected; tests use a temp file, live runs use
``AI_MCP_CRM_PATH``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)

READ_ONLY = ToolAnnotations(read_only=True, destructive=False, idempotent=True, open_world=False)
WRITE = ToolAnnotations(read_only=False, destructive=False, idempotent=False, open_world=False)


class CrmStore:
    """A JSON-file lead store. One file, plain dicts, atomic rewrites."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, Any] = {"next_id": 1, "leads": []}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, fields: dict[str, str]) -> JsonDict:
        lead: JsonDict = {
            "id": f"lead-{self._data['next_id']:04d}",
            **fields,
            "activities": [],
        }
        self._data["next_id"] += 1
        self._data["leads"].append(lead)
        self._save()
        return lead

    def find(self, key: str) -> JsonDict | None:
        for lead in self._data["leads"]:
            if lead["id"] == key or lead.get("email", "").lower() == key.lower():
                return lead
        return None

    def all(self) -> list[JsonDict]:
        leads: list[JsonDict] = self._data["leads"]
        return leads

    def log(self, key: str, activity: str) -> JsonDict:
        lead = self.find(key)
        if lead is None:
            raise ToolError(f"No lead found for {key!r}")
        entry = {
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "activity": activity,
        }
        lead["activities"].append(entry)
        self._save()
        return lead


def _render_lead(lead: JsonDict) -> str:
    lines = [
        f"{lead['id']} — {lead.get('name', '')}",
        f"  email: {lead.get('email', '')} · phone: {lead.get('phone', '')}",
        f"  company: {lead.get('company', '')} · source: {lead.get('source', '')}",
    ]
    if lead.get("notes"):
        lines.append(f"  notes: {lead['notes']}")
    for entry in lead.get("activities", []):
        lines.append(f"  [{entry['at']}] {entry['activity']}")
    return "\n".join(lines)


def create_server(path: Path) -> McpServer:
    """Build the mini-crm server persisting to the JSON file at ``path``."""
    store = CrmStore(path)
    server = McpServer(
        "mini-crm",
        instructions=f"A tiny local CRM. Data file: {path} (JSON, on this machine only).",
    )

    def add_lead(arguments: JsonDict) -> ToolResult:
        fields = {
            key: str(arguments.get(key, ""))
            for key in ("name", "email", "phone", "company", "source", "notes")
        }
        if not fields["name"]:
            raise ToolError("add_lead needs at least a name.")
        lead = store.add(fields)
        return ToolResult(text=_render_lead(lead), structured={"lead": lead})

    def get_lead(arguments: JsonDict) -> ToolResult:
        lead = store.find(str(arguments["key"]))
        if lead is None:
            raise ToolError(f"No lead found for {arguments['key']!r}")
        return ToolResult(text=_render_lead(lead), structured={"lead": lead})

    def list_leads(arguments: JsonDict) -> ToolResult:
        leads = store.all()
        text = "\n".join(_render_lead(lead) for lead in leads) or "(no leads yet)"
        return ToolResult(text=text, structured={"leads": leads})

    def log_activity(arguments: JsonDict) -> ToolResult:
        lead = store.log(str(arguments["key"]), str(arguments["activity"]))
        return ToolResult(
            text=f"Logged on {lead['id']}: {arguments['activity']}",
            structured={"lead": lead},
        )

    server.add_tool(
        Tool(
            name="add_lead",
            description="Add a lead to the local CRM and return its id.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "company": {"type": "string"},
                    "source": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["name"],
            },
            handler=add_lead,
            annotations=WRITE,
        )
    )
    server.add_tool(
        Tool(
            name="get_lead",
            description="Fetch one lead by id (lead-0001) or email address.",
            input_schema={
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
            handler=get_lead,
            annotations=READ_ONLY,
        )
    )
    server.add_tool(
        Tool(
            name="list_leads",
            description="List every lead in the local CRM.",
            input_schema={"type": "object", "properties": {}},
            handler=list_leads,
            annotations=READ_ONLY,
        )
    )
    server.add_tool(
        Tool(
            name="log_activity",
            description="Append a timestamped activity note to a lead's history.",
            input_schema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Lead id or email."},
                    "activity": {"type": "string"},
                },
                "required": ["key", "activity"],
            },
            handler=log_activity,
            annotations=WRITE,
        )
    )
    server.add_resource(
        Resource(
            uri="crm://summary",
            name="CRM summary",
            description="Lead counts for the local store.",
            reader=lambda: f"{len(store.all())} leads in the local CRM at {path}.",
        )
    )
    return server
