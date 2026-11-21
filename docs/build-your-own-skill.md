# Build your own skill — Skill 05 is yours

Servers give an agent hands. A skill teaches it a job: when the job
applies, the steps, and the rules that keep it safe. The four skills in
`skills/` follow one format — the Agent Skills format — and yours
should too.

## The format

A skill is a folder. The folder name is the skill's name. Inside, one
required file:

```text
skills/
└── your-skill-name/
    ├── SKILL.md            # required: frontmatter + instructions
    └── references/         # optional: checklists, rubrics, examples
        └── checklist.md
```

`SKILL.md` opens with YAML frontmatter carrying exactly two required
fields, then the instructions in Markdown:

```markdown
---
name: your-skill-name
description: What the skill does and when to use it. The description is
  what an agent reads to decide whether the skill applies — name the
  task, the trigger, and any hard limit.
---

# Your Skill Name

## Workflow

1. Steps, in order, naming the exact tools and servers.
2. Mark where the agent stops and shows a human something.

## Rules

- What this skill never does.
- What happens when inputs are missing (ask or stop — never invent).
```

## The rules the validator enforces

`ai-mcp validate-skill skills/your-skill-name` checks:

- `SKILL.md` exists and opens with a closed `---` frontmatter block.
- `name` is present, lowercase kebab-case, ≤ 64 characters, and equal
  to the folder name.
- `description` is present and ≤ 1024 characters.

Run it before you commit. The shipped template
(`skills/templates/skill-template/`) passes validation as-is — start
by copying it.

## Writing a skill that earns its keep

1. **The description is a trigger, not a summary.** "Use when the user
   provides a CSV of leads or asks to check a list before a campaign"
   beats "Helps with leads." Agents route on this text.
2. **Steps name tools.** "Run `check_lead_list` on the lead-tools
   server" is a step. "Check the list" is a wish.
3. **Rules are limits, not advice.** "Never contact C-grade rows" can
   be followed and audited; "be careful with bad leads" cannot.
4. **Push detail into references.** The main file stays lean enough to
   load every time; checklists and rubrics live in `references/` and
   load on demand.
5. **Say what done looks like.** The report, the artifact, the stopping
   point. A skill that ends with "and then handle it" isn't finished.

## Pairing a skill with a server

The strongest pattern in this repo: the skill carries the *discipline*
and the server carries the *capability*. `phone-outreach-guardrails`
(scrub, approval, reporting) wraps `phone-tools` (the guarded tools);
`lead-list-checker` wraps `lead-tools`. When you add a server
(`docs/build-your-own-server.md`), ask whether its safe use deserves a
skill of its own — for anything that acts on the world, the answer is
yes.
