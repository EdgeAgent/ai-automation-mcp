---
name: lead-list-checker
description: Grade and clean a lead list before any outreach. Use when the user provides a CSV of leads (names, emails, phones) or asks to check, clean, dedupe, or score leads before a campaign. Runs the lead-tools MCP server (Server 01): check_lead_list for a whole list, score_lead for one lead. Never skip the check and never contact C-grade rows.
---

# Lead List Checker

A lead list is guilty until checked. Sending to duplicates, dead emails,
and undialable phones burns the sender domain for every future campaign —
so the list gets graded before anyone drafts a word of outreach.

## Workflow

1. **Read the rubric first.** Fetch the `rubric://lead-grading` resource
   from the lead-tools server so your report uses the same A/B/C language
   the tools use. (A copy lives in `references/grading-rubric.md`.)
2. **Run `check_lead_list`** with the full CSV text. It dedupes by
   normalized email (phone fallback), flags problems per row, grades
   every kept row, and returns the cleaned CSV plus run statistics.
3. **Report before acting.** Give the user: rows in, rows kept,
   duplicates removed, the A/B/C counts, and every flag that appeared.
   Ask which grades may be contacted. Default answer: A only; B when the
   user accepts the gap; C never.
4. **For a single lead**, use `score_lead` and report the grade with its
   reasons (the flags), not just the letter.

## Rules

- The cleaned CSV is the only list downstream steps may use. Never work
  from the raw list after a check has run.
- A grade measures *reachability*, not intent. Never describe an A-grade
  lead as "likely to buy."
- If the CSV has no header row or a required column is unrecognizable,
  say so and stop — do not guess at the mapping silently.
- This skill never sends anything. Outreach is a separate, approved step.
