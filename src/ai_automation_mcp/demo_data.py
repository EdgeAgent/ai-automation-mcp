"""Sample inputs for the demos: a messy lead list and canned web pages."""

SAMPLE_LEAD_CSV = """name,email,phone,company,source
Dana Whitfield,dana@example.com,(313) 555-0142,Whitfield Holdings,webinar
Marcus Reid,marcus@example.com,313-555-0117,Reid Properties,referral
Dana Whitfield,dana@example.com,(313) 555-0142,Whitfield Holdings,webinar
Priya Nair,priya@,555-0143,Nair Group,trade show
Tom Okafor,,(248) 555-0190,Okafor Ventures,webinar
,noname@example.com,(517) 555-0123,,cold list
"""

SAMPLE_QUOTE_ARGUMENTS = {
    "client": "Riverside Dental",
    "items": [
        {"description": "AI receptionist setup", "quantity": 1, "unit_price": 400},
        {"description": "Call-flow design", "quantity": 2, "unit_price": 150},
    ],
    "tax_rate": 13,
    "deposit_percent": 30,
}

DEMO_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
<title>Edge Agency — AI Receptionists for Local Business</title>
<style>body { color: red; }</style>
<script>console.log("tracking");</script>
</head>
<body>
<h1>Never miss a call again</h1>
<p>Our AI receptionist answers in under a second, books the appointment,
and texts you the summary.</p>
<p>Setup takes one call. Flat monthly pricing, no per-minute traps.</p>
</body>
</html>
"""

DEMO_PAGES = {
    "https://example.com/receptionist": DEMO_PAGE_HTML,
}
