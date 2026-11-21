# Grading rubric (summary)

The full rubric is the `rubric://lead-grading` resource on the
lead-tools server. This copy is for offline reference; if the two ever
disagree, the server resource wins.

- **A — ready.** Name + valid email + valid phone (10 digits after
  normalization).
- **B — usable with a gap.** Name + exactly one valid contact channel.
- **C — incomplete.** Missing name, or no valid contact channel.

Flags: `missing_email`, `invalid_email`, `missing_phone`,
`invalid_phone`, `missing_name`. Duplicates are detected by normalized
email (phone fallback), dropped after the first occurrence, and counted
in the run statistics — never silently.
