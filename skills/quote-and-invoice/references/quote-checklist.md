# Quote checklist

Before calling `build_quote`, confirm each of these with the user or
from their message — ask about anything missing:

- [ ] Client name exactly as it should appear on the document
- [ ] Every line item: description, quantity, unit price
- [ ] Labor, if any: hours and hourly rate
- [ ] Markup percent, if the user's pricing uses one
- [ ] Tax rate for the client's jurisdiction
- [ ] Deposit percent (default 30%)

Before calling `create_invoice`, confirm:

- [ ] The user approved the rendered quote, unchanged
- [ ] Invoice number, if the user runs their own numbering
- [ ] Issue date and due window (default: today, due in 14 days)
