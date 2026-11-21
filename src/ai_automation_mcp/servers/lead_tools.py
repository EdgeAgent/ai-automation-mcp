"""Server 01 — lead-tools.

The deterministic end of the path: no model, no network, no cost. Two
tools over one pure-stdlib cleaning core (the same grading pattern as
Step 2's Recipe 01, exposed here as MCP tools):

- ``check_lead_list`` — a whole CSV in → dedupe, invalid-contact flags,
  A/B/C grades, and the cleaned CSV out.
- ``score_lead`` — one lead in → its grade and the reasons.

Grades: **A** name + valid email + valid phone (ready), **B** name + one
valid channel (usable with a gap), **C** missing name or no valid channel
(incomplete). The rubric is also a resource (``rubric://lead-grading``)
so a client can read the rules before trusting the grades.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Literal

from pydantic import BaseModel, Field

from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Prompt,
    PromptArgument,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
FIELDS = ["name", "email", "phone", "company", "source"]
Grade = Literal["A", "B", "C"]

RUBRIC = """# Lead grading rubric

Every lead is graded on contact completeness — nothing else. A high grade
means the lead is *reachable*, not that it will buy.

- **A — ready.** Name present, email syntactically valid, phone dialable
  (10 digits, North-American style after normalization).
- **B — usable with a gap.** Name present and exactly one of email /
  phone is valid.
- **C — incomplete.** Name missing, or neither contact channel is valid.

Flags name the specific problem per row: `missing_email`,
`invalid_email`, `missing_phone`, `invalid_phone`, `missing_name`.
Duplicates are detected by normalized email (falling back to normalized
phone), dropped after the first occurrence, and counted in the stats.
Always check a list before outreach: sending to C-grade rows burns the
sender domain for everyone.
"""

READ_ONLY = ToolAnnotations(read_only=True, destructive=False, idempotent=True, open_world=False)


class CleanedLead(BaseModel):
    """One deduplicated lead row with validation flags and a grade."""

    name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    source: str = ""
    flags: list[str] = Field(default_factory=list)
    grade: Grade = "C"


class CleanResult(BaseModel):
    """The outcome of a cleaning run: rows, rendered CSV, and statistics."""

    rows: list[CleanedLead]
    cleaned_csv: str
    stats: dict[str, int]


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def valid_email(email: str) -> bool:
    """Return True for a syntactically plausible email address."""
    return bool(EMAIL_RE.match(email.strip()))


def valid_phone(phone: str) -> bool:
    """Return True for a dialable North-American-style number (10 digits)."""
    return len(_normalize_phone(phone)) == 10


def grade_lead(name: str, email: str, phone: str) -> tuple[Grade, list[str]]:
    """Grade one lead and return the grade plus per-problem flags."""
    flags: list[str] = []
    email_ok = valid_email(email) if email else False
    phone_ok = valid_phone(phone) if phone else False
    if not email:
        flags.append("missing_email")
    elif not email_ok:
        flags.append("invalid_email")
    if not phone:
        flags.append("missing_phone")
    elif not phone_ok:
        flags.append("invalid_phone")
    if not name:
        flags.append("missing_name")
    if not name:
        return "C", flags
    if email_ok and phone_ok:
        return "A", flags
    if email_ok or phone_ok:
        return "B", flags
    return "C", flags


def clean_leads(csv_text: str) -> CleanResult:
    """Clean ``csv_text``: dedupe, flag, grade, and re-render as CSV."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ToolError("CSV input has no header row.")
    seen: set[str] = set()
    rows: list[CleanedLead] = []
    duplicates = 0
    total_in = 0
    for raw_row in reader:
        total_in += 1
        row = {field: (raw_row.get(field) or "").strip() for field in FIELDS}
        email_key = row["email"].lower()
        phone_key = _normalize_phone(row["phone"])
        dedupe_key = f"email:{email_key}" if email_key else f"phone:{phone_key}"
        if dedupe_key in seen and (email_key or phone_key):
            duplicates += 1
            continue
        seen.add(dedupe_key)
        grade, flags = grade_lead(row["name"], row["email"], row["phone"])
        rows.append(CleanedLead(**row, flags=flags, grade=grade))

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[*FIELDS, "grade", "flags"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **row.model_dump(exclude={"flags", "grade"}),
                "grade": row.grade,
                "flags": ";".join(row.flags),
            }
        )
    stats = {
        "input_rows": total_in,
        "kept_rows": len(rows),
        "duplicates_removed": duplicates,
        "grade_a": sum(1 for row in rows if row.grade == "A"),
        "grade_b": sum(1 for row in rows if row.grade == "B"),
        "grade_c": sum(1 for row in rows if row.grade == "C"),
        "invalid_emails": sum(1 for row in rows if "invalid_email" in row.flags),
        "invalid_phones": sum(1 for row in rows if "invalid_phone" in row.flags),
    }
    return CleanResult(rows=rows, cleaned_csv=output.getvalue(), stats=stats)


def _check_lead_list(arguments: JsonDict) -> ToolResult:
    result = clean_leads(str(arguments["csv_text"]))
    summary = (
        f"{result.stats['kept_rows']} leads kept "
        f"({result.stats['duplicates_removed']} duplicates removed): "
        f"A={result.stats['grade_a']} B={result.stats['grade_b']} "
        f"C={result.stats['grade_c']}"
    )
    return ToolResult(
        text=f"{summary}\n\n{result.cleaned_csv}",
        structured={"stats": result.stats, "cleaned_csv": result.cleaned_csv},
    )


def _score_lead(arguments: JsonDict) -> ToolResult:
    name = str(arguments.get("name", ""))
    email = str(arguments.get("email", ""))
    phone = str(arguments.get("phone", ""))
    grade, flags = grade_lead(name, email, phone)
    reasons = ", ".join(flags) if flags else "name, email, and phone all check out"
    return ToolResult(
        text=f"Grade {grade} — {reasons}.",
        structured={"grade": grade, "flags": flags},
    )


def _outreach_plan(arguments: dict[str, str]) -> list[JsonDict]:
    context = arguments.get("context", "a new outreach campaign")
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": (
                    f"I am preparing {context}. First read the grading rubric "
                    "resource (rubric://lead-grading). Then, when I give you the "
                    "lead list as CSV, run check_lead_list on it and report the "
                    "grade counts and every flag. Do not draft any outreach until "
                    "I confirm the cleaned list — C-grade rows never get contacted."
                ),
            },
        }
    ]


def create_server() -> McpServer:
    """Build the lead-tools server (no backends: pure local logic)."""
    server = McpServer(
        "lead-tools",
        instructions="Check and grade lead lists before any outreach. Local only.",
    )
    server.add_tool(
        Tool(
            name="check_lead_list",
            description=(
                "Clean a lead list CSV: dedupe by email/phone, flag invalid or "
                "missing contacts per row, grade every kept row A/B/C, and "
                "return the cleaned CSV with run statistics."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "csv_text": {
                        "type": "string",
                        "description": "CSV with header: name,email,phone,company,source",
                    }
                },
                "required": ["csv_text"],
            },
            handler=_check_lead_list,
            annotations=ToolAnnotations(
                read_only=True,
                destructive=False,
                idempotent=True,
                open_world=False,
                title="Check a lead list",
            ),
        )
    )
    server.add_tool(
        Tool(
            name="score_lead",
            description="Grade a single lead A/B/C from its name, email, and phone.",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["name", "email", "phone"],
            },
            handler=_score_lead,
            annotations=READ_ONLY,
        )
    )
    server.add_resource(
        Resource(
            uri="rubric://lead-grading",
            name="Lead grading rubric",
            description="The A/B/C grading rules check_lead_list and score_lead apply.",
            reader=lambda: RUBRIC,
            mime_type="text/markdown",
        )
    )
    server.add_prompt(
        Prompt(
            name="outreach_plan",
            description="A pre-outreach routine: read the rubric, check the list, then stop.",
            arguments=[
                PromptArgument(
                    name="context",
                    description="What the outreach is for, e.g. 'a Detroit wholesaler campaign'.",
                    required=False,
                )
            ],
            getter=_outreach_plan,
        )
    )
    return server
