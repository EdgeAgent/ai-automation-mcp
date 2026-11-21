---
name: quote-and-invoice
description: Build an itemized quote, get it approved, then create the matching invoice. Use when the user asks to quote a job, price work, or invoice a client. Runs the business-tools MCP server (Server 02): build_quote for the quote, create_invoice only after the user approves the quote. Money math is exact Decimal arithmetic — never recompute totals by hand or round differently.
---

# Quote and Invoice

Two documents, one rule: the quote is a draft until the user approves
it, and the invoice is created only from the approved quote — with the
same items, the same rates, and the same totals.

## Workflow

1. **Break the job into lines.** Each line needs a description, a
   quantity, and a unit price. If a price is unknown, ask — never invent
   a number for someone else's business.
2. **Call `build_quote`** with the items, plus labor (hours × rate),
   markup percent, and tax rate when they apply. The tool computes in
   exact decimal arithmetic; the deposit and balance always sum to the
   total.
3. **Show the rendered quote to the user and stop.** No invoice exists
   until the user approves the quote as shown. If they change anything,
   rebuild the quote — do not patch numbers in conversation.
4. **On approval, call `create_invoice`** with the identical items and
   tax rate. Pass an explicit `invoice_number` or `issue_date` /
   `due_days` when the user provides them; otherwise accept the server's
   defaults and report them.

## Rules

- Never state a total you did not get from the tool. If the user asks
  "about how much," still run the tool and quote its number.
- The standard terms live in the `templates://invoice-terms` resource;
  read it before answering questions about due dates or deposits.
- An issued invoice is never edited. A correction is a new document —
  say so plainly if the user asks to "just change" one.
