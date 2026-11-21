"""Parse and validate Agent Skills (SKILL.md folders).

The Agent Skills format is deliberately small: a folder with a
``SKILL.md`` whose YAML frontmatter carries ``name`` and ``description``,
plus optional bundled resources the agent loads on demand. This module
checks the rules a client enforces when it loads a skill:

- the file is named ``SKILL.md`` and opens with a closed frontmatter block;
- ``name`` is present, lowercase-hyphen (kebab-case), at most 64 chars,
  and matches the folder name;
- ``description`` is present and at most 1024 chars — it is what the
  agent reads to decide when the skill applies, so it must say what the
  skill does *and* when to use it.

The frontmatter parser is intentionally minimal — flat ``key: value``
scalars only, which is all the required fields use. It is not a general
YAML parser, and the docs say so.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024


@dataclass
class SkillReport:
    """Validation outcome for one skill folder."""

    path: Path
    name: str | None = None
    description: str | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    """Extract flat frontmatter fields from SKILL.md text."""
    problems: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md must open with a '---' frontmatter block."]
    fields: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        if not line.strip():
            continue
        if ":" not in line:
            problems.append(f"Frontmatter line is not 'key: value': {line!r}")
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        fields[key.strip()] = value
    if not closed:
        problems.append("Frontmatter block is never closed with '---'.")
    return fields, problems


def validate_skill(path: Path) -> SkillReport:
    """Validate the skill at ``path`` (a folder, or a SKILL.md file)."""
    skill_file = path if path.name == "SKILL.md" else path / "SKILL.md"
    folder = skill_file.parent
    report = SkillReport(path=folder)
    if not skill_file.is_file():
        report.problems.append(f"No SKILL.md found in {folder}.")
        return report

    fields, problems = parse_frontmatter(skill_file.read_text(encoding="utf-8"))
    report.problems.extend(problems)

    name = fields.get("name", "")
    if not name:
        report.problems.append("Frontmatter is missing the required 'name' field.")
    else:
        report.name = name
        if len(name) > MAX_NAME_LENGTH:
            report.problems.append(f"name is {len(name)} chars; the limit is {MAX_NAME_LENGTH}.")
        if not NAME_RE.match(name):
            report.problems.append(
                f"name {name!r} must be lowercase kebab-case (letters, digits, hyphens)."
            )
        if folder.name != name:
            report.problems.append(
                f"Folder name {folder.name!r} does not match skill name {name!r}."
            )

    description = fields.get("description", "")
    if not description:
        report.problems.append("Frontmatter is missing the required 'description' field.")
    else:
        report.description = description
        if len(description) > MAX_DESCRIPTION_LENGTH:
            report.problems.append(
                f"description is {len(description)} chars; the limit is {MAX_DESCRIPTION_LENGTH}."
            )
    return report
