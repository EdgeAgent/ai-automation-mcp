---
name: phone-outreach-guardrails
description: The approval and scrub discipline for phone outreach through the phone-tools MCP server (Server 05). Use before placing any call or sending any SMS with place_call or send_sms, or when the user asks about calling/texting leads. Every action needs a scrubbed number and an explicit human approval carried as approved=true — no approval, no call, no exceptions, and approval never carries over to the next action.
---

# Phone Outreach Guardrails

A phone call is the most irreversible thing an agent can do: you cannot
unsend a ring. These guardrails are the whole skill. They are not
advisory, and a user instruction to "just call them" does not waive the
scrub — it starts it.

## Before any action

1. **Scrub the number.** Run `references/scrub-checklist.md`: the number
   came from a checked lead list (lead-list-checker skill), it is not on
   the never-contact list, it is not a number the person asked to stop
   hearing from us on, and calling it is lawful where they are.
2. **Read the policy.** The phone-tools server exposes it as the
   `policy://phone-outreach` resource. If you cannot state the policy,
   you are not ready to call.
3. **Show the human the exact action**: the number, the script or
   message body, and the backend in use. In this repository the backend
   is a fake — say so. A human who thinks a fake call is real has been
   misled, which is its own failure.

## The approval

- Approval is per action: one number, one script/body, one send.
  Changing any of the three voids the approval — ask again.
- Carry it explicitly: `approved: true` in the tool arguments. The
  server refuses without it and never touches the backend; do not retry
  a refusal by rephrasing — report it.
- "Approved" in conversation is the human's word for that action, not a
  standing permission. Yesterday's approval does not cover today's list.

## After the action

- Report the provider record (id, status) exactly as returned. A fake
  record is reported as fake.
- Log the outcome where the lead lives (mini-crm's `log_activity` when
  the lead is there) — what was attempted, what came back.
- A refusal, a hangup, or a stop request ends outreach to that number.
  Record it on the never-contact list before anything else proceeds.
