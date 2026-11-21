"""Server 02 — business-tools.

Money documents, computed deterministically in ``Decimal`` (the same
pattern as Step 2's Recipe 02, exposed as MCP tools):

- ``build_quote`` — items + labor + markup + tax → totals and a
  deposit/balance split that always sums to the total. Pure: read-only.
- ``create_invoice`` — the same math as a numbered invoice with an
  issue date and a due date, kept in the server's in-memory ledger.

JSON numbers arrive as int/float; they are converted through
``Decimal(str(value))`` so a price of 19.99 stays 19.99, never
19.989999… — a money document must recompute cent-for-cent.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

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

CENTS = Decimal("0.01")

TERMS = """# Standard invoice terms

- Payment is due on the due date printed on the invoice.
- The deposit shown on a quote is due before work starts; the balance is
  due on completion.
- Amounts are computed in exact decimal arithmetic and rounded half-up
  to the cent at each step, so every document recomputes cent-for-cent.
- Disputes: raise them before the due date so the ledger can be corrected
  with a new document — issued invoices are never edited in place.
"""


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def _decimal(value: object, field_name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ToolError(f"{field_name} must be a number, got {value!r}") from exc


class QuoteItem(BaseModel):
    """One itemized line: a description, a quantity, and a unit price."""

    description: str
    quantity: Decimal = Decimal(1)
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _money(self.quantity * self.unit_price)


class QuoteRequest(BaseModel):
    """Everything needed to draft a quote."""

    client: str
    items: list[QuoteItem] = Field(min_length=1)
    labor_hours: Decimal = Decimal(0)
    labor_rate: Decimal = Decimal(0)
    markup_percent: Decimal = Decimal(0)
    tax_rate: Decimal = Decimal(0)
    deposit_percent: Decimal = Decimal(30)


class Quote(BaseModel):
    """A computed quote. ``deposit_due + balance_due == total`` always."""

    client: str
    items: list[QuoteItem]
    items_subtotal: Decimal
    labor_total: Decimal
    subtotal: Decimal
    markup_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    deposit_due: Decimal
    balance_due: Decimal
    tax_rate: Decimal
    deposit_percent: Decimal

    def render(self) -> str:
        lines = [f"QUOTE — prepared for {self.client}", ""]
        for item in self.items:
            lines.append(
                f"- {item.description}: {item.quantity} x ${item.unit_price} = ${item.line_total}"
            )
        if self.labor_total:
            lines.append(f"- Labor: ${self.labor_total}")
        lines.append("")
        lines.append(f"Subtotal: ${self.subtotal}")
        if self.markup_amount:
            lines.append(f"Markup: ${self.markup_amount}")
        lines.append(f"Tax ({self.tax_rate}%): ${self.tax_amount}")
        lines.append(f"Total: ${self.total}")
        lines.append(f"Deposit due ({self.deposit_percent}%): ${self.deposit_due}")
        lines.append(f"Balance on completion: ${self.balance_due}")
        return "\n".join(lines)


class Invoice(BaseModel):
    """A computed invoice: a quote's math plus number and dates."""

    number: str
    client: str
    issue_date: str
    due_date: str
    items: list[QuoteItem]
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_due: Decimal
    tax_rate: Decimal

    def render(self) -> str:
        lines = [
            f"INVOICE {self.number} — {self.client}",
            f"Issued: {self.issue_date} · Due: {self.due_date}",
            "",
        ]
        for item in self.items:
            lines.append(
                f"- {item.description}: {item.quantity} x ${item.unit_price} = ${item.line_total}"
            )
        lines.append("")
        lines.append(f"Subtotal: ${self.subtotal}")
        lines.append(f"Tax ({self.tax_rate}%): ${self.tax_amount}")
        lines.append(f"Total: ${self.total}")
        lines.append(f"Amount due: ${self.amount_due}")
        return "\n".join(lines)


def build_quote(request: QuoteRequest) -> Quote:
    """Compute a quote from ``request``. Pure function; no side effects."""
    items_subtotal = _money(sum((item.line_total for item in request.items), Decimal(0)))
    labor_total = _money(request.labor_hours * request.labor_rate)
    subtotal = _money(items_subtotal + labor_total)
    markup_amount = _money(subtotal * request.markup_percent / Decimal(100))
    taxable = subtotal + markup_amount
    tax_amount = _money(taxable * request.tax_rate / Decimal(100))
    total = _money(taxable + tax_amount)
    deposit_due = _money(total * request.deposit_percent / Decimal(100))
    balance_due = _money(total - deposit_due)
    return Quote(
        client=request.client,
        items=request.items,
        items_subtotal=items_subtotal,
        labor_total=labor_total,
        subtotal=subtotal,
        markup_amount=markup_amount,
        tax_amount=tax_amount,
        total=total,
        deposit_due=deposit_due,
        balance_due=balance_due,
        tax_rate=request.tax_rate,
        deposit_percent=request.deposit_percent,
    )


def _parse_items(raw: object) -> list[QuoteItem]:
    if not isinstance(raw, list) or not raw:
        raise ToolError("items must be a non-empty array of line items.")
    items: list[QuoteItem] = []
    for entry in raw:
        if not isinstance(entry, dict) or "description" not in entry or "unit_price" not in entry:
            raise ToolError("Each item needs a description and a unit_price.")
        items.append(
            QuoteItem(
                description=str(entry["description"]),
                quantity=_decimal(entry.get("quantity", 1), "quantity"),
                unit_price=_decimal(entry["unit_price"], "unit_price"),
            )
        )
    return items


def _request_from(arguments: JsonDict) -> QuoteRequest:
    return QuoteRequest(
        client=str(arguments.get("client", "")),
        items=_parse_items(arguments.get("items")),
        labor_hours=_decimal(arguments.get("labor_hours", 0), "labor_hours"),
        labor_rate=_decimal(arguments.get("labor_rate", 0), "labor_rate"),
        markup_percent=_decimal(arguments.get("markup_percent", 0), "markup_percent"),
        tax_rate=_decimal(arguments.get("tax_rate", 0), "tax_rate"),
        deposit_percent=_decimal(arguments.get("deposit_percent", 30), "deposit_percent"),
    )


_ITEMS_SCHEMA: JsonDict = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "quantity": {"type": "number"},
            "unit_price": {"type": "number"},
        },
        "required": ["description", "unit_price"],
    },
}


class BusinessTools:
    """Stateful server factory: the invoice ledger lives on the instance."""

    def __init__(self) -> None:
        self.invoices: list[Invoice] = []

    def _build_quote(self, arguments: JsonDict) -> ToolResult:
        quote = build_quote(_request_from(arguments))
        return ToolResult(
            text=quote.render(),
            structured={"quote": quote.model_dump(mode="json")},
        )

    def _create_invoice(self, arguments: JsonDict) -> ToolResult:
        request = _request_from(arguments)
        quote = build_quote(request)
        number = str(arguments.get("invoice_number") or f"INV-{len(self.invoices) + 1:04d}")
        issue_raw = str(arguments.get("issue_date") or date.today().isoformat())
        try:
            issued = date.fromisoformat(issue_raw)
        except ValueError as exc:
            raise ToolError(f"issue_date must be YYYY-MM-DD, got {issue_raw!r}") from exc
        due_days = int(arguments.get("due_days", 14))
        invoice = Invoice(
            number=number,
            client=request.client,
            issue_date=issued.isoformat(),
            due_date=(issued + timedelta(days=due_days)).isoformat(),
            items=request.items,
            subtotal=quote.subtotal,
            tax_amount=quote.tax_amount,
            total=quote.total,
            amount_due=quote.total,
            tax_rate=request.tax_rate,
        )
        self.invoices.append(invoice)
        return ToolResult(
            text=invoice.render(),
            structured={"invoice": invoice.model_dump(mode="json")},
        )

    def server(self) -> McpServer:
        server = McpServer(
            "business-tools",
            instructions="Deterministic quote and invoice math. No network.",
        )
        server.add_tool(
            Tool(
                name="build_quote",
                description=(
                    "Compute an itemized quote: line items, labor, markup, tax, "
                    "total, and a deposit/balance split. Pure math, no side effects."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "client": {"type": "string"},
                        "items": _ITEMS_SCHEMA,
                        "labor_hours": {"type": "number"},
                        "labor_rate": {"type": "number"},
                        "markup_percent": {"type": "number"},
                        "tax_rate": {"type": "number"},
                        "deposit_percent": {"type": "number"},
                    },
                    "required": ["client", "items"],
                },
                handler=self._build_quote,
                annotations=ToolAnnotations(
                    read_only=True,
                    destructive=False,
                    idempotent=True,
                    open_world=False,
                    title="Build a quote",
                ),
            )
        )
        server.add_tool(
            Tool(
                name="create_invoice",
                description=(
                    "Create a numbered invoice with issue/due dates and exact "
                    "totals, recorded in this server's in-memory ledger."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "client": {"type": "string"},
                        "items": _ITEMS_SCHEMA,
                        "tax_rate": {"type": "number"},
                        "invoice_number": {"type": "string"},
                        "issue_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "due_days": {"type": "integer"},
                    },
                    "required": ["client", "items"],
                },
                handler=self._create_invoice,
                annotations=ToolAnnotations(
                    read_only=False,
                    destructive=False,
                    idempotent=False,
                    open_world=False,
                    title="Create an invoice",
                ),
            )
        )
        server.add_resource(
            Resource(
                uri="templates://invoice-terms",
                name="Standard invoice terms",
                description="The payment terms that accompany invoices from this server.",
                reader=lambda: TERMS,
                mime_type="text/markdown",
            )
        )
        server.add_prompt(
            Prompt(
                name="quote_request",
                description="Gather a client's job details, then call build_quote.",
                arguments=[
                    PromptArgument(name="client", description="Client name.", required=True),
                    PromptArgument(
                        name="job",
                        description="Plain-language description of the job.",
                        required=True,
                    ),
                ],
                getter=self._quote_prompt,
            )
        )
        return server

    @staticmethod
    def _quote_prompt(arguments: dict[str, str]) -> list[JsonDict]:
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Prepare a quote for {arguments['client']} for this job: "
                        f"{arguments['job']}. Break the job into itemized lines with "
                        "quantities and unit prices, ask me about anything you cannot "
                        "price, then call build_quote with the items, the tax rate I "
                        "confirm, and a 30% deposit. Show me the rendered quote before "
                        "creating any invoice."
                    ),
                },
            }
        ]


def create_server() -> McpServer:
    """Build the business-tools server with a fresh invoice ledger."""
    return BusinessTools().server()
