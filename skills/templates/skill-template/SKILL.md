---
name: skill-template
description: A template for writing a new Agent Skill in this pack. Replace this description with what the skill does and when to use it — the description is what an agent reads to decide whether the skill applies, so name the task, the trigger, and any hard limits (for example, "draft-only, never sends").
---

# Skill Template

Copy this folder, rename it to your skill's name, and rewrite this file.
The folder name must match the `name` in the frontmatter above — the
validator (`ai-mcp validate-skill <folder>`) enforces it.

## When this skill applies

State the trigger plainly: the request, the file type, the situation.
An agent should be able to decide "this skill, yes/no" from the
description plus this section alone.

## Workflow

1. Numbered steps, in order, each one an action the agent can take.
2. Name the exact tools (and which server they live on) at each step.
3. Mark the stopping points: where the agent must show a human
   something and wait.

## Rules

- The hard limits, stated as rules: what this skill never does.
- What it does when inputs are missing or wrong (ask, stop — never
  invent).
- Where the outputs go, and what "done" looks like.

## References

Link bundled files here (for example `references/checklist.md`) and say
when the agent should load each one. References are read on demand, so
keep the main file lean and push detail into them.
