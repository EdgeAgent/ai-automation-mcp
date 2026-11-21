"""The skills validator: shipped skills pass, broken fixtures fail."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_automation_mcp.skills import validate_skill

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
SHIPPED = ["lead-list-checker", "quote-and-invoice", "inbox-triage", "phone-outreach-guardrails"]


@pytest.mark.parametrize("name", SHIPPED)
def test_shipped_skills_are_valid(name: str) -> None:
    report = validate_skill(SKILLS_DIR / name)
    assert report.ok, report.problems
    assert report.name == name


def test_template_is_valid() -> None:
    report = validate_skill(SKILLS_DIR / "templates" / "skill-template")
    assert report.ok, report.problems


def _make_skill(tmp_path: Path, folder: str, frontmatter: str) -> Path:
    skill_dir = tmp_path / folder
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(frontmatter, encoding="utf-8")
    return skill_dir


def test_missing_skill_file(tmp_path: Path) -> None:
    report = validate_skill(tmp_path / "nothing-here")
    assert not report.ok
    assert any("No SKILL.md" in problem for problem in report.problems)


def test_missing_frontmatter(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, "plain", "# Just a heading\n")
    report = validate_skill(skill)
    assert not report.ok
    assert any("frontmatter" in problem for problem in report.problems)


def test_unclosed_frontmatter(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, "open", "---\nname: open\ndescription: never closed\n")
    report = validate_skill(skill)
    assert not report.ok
    assert any("never closed" in problem for problem in report.problems)


def test_missing_name(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, "noname", "---\ndescription: Does a thing.\n---\n")
    report = validate_skill(skill)
    assert not report.ok
    assert any("'name'" in problem for problem in report.problems)


def test_missing_description(tmp_path: Path) -> None:
    skill = _make_skill(tmp_path, "nodesc", "---\nname: nodesc\n---\n")
    report = validate_skill(skill)
    assert not report.ok
    assert any("'description'" in problem for problem in report.problems)


def test_bad_name_format(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path, "Bad_Name", "---\nname: Bad_Name\ndescription: Does a thing.\n---\n"
    )
    report = validate_skill(skill)
    assert not report.ok
    assert any("kebab-case" in problem for problem in report.problems)


def test_name_too_long(tmp_path: Path) -> None:
    long_name = "a" * 65
    skill = _make_skill(
        tmp_path, long_name, f"---\nname: {long_name}\ndescription: Does a thing.\n---\n"
    )
    report = validate_skill(skill)
    assert not report.ok
    assert any("64" in problem for problem in report.problems)


def test_description_too_long(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path,
        "wordy",
        f"---\nname: wordy\ndescription: {'x' * 1025}\n---\n",
    )
    report = validate_skill(skill)
    assert not report.ok
    assert any("1024" in problem for problem in report.problems)


def test_folder_name_mismatch(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path, "folder-name", "---\nname: other-name\ndescription: Does a thing.\n---\n"
    )
    report = validate_skill(skill)
    assert not report.ok
    assert any("does not match" in problem for problem in report.problems)


def test_quoted_description_is_unquoted(tmp_path: Path) -> None:
    skill = _make_skill(
        tmp_path,
        "quoted",
        '---\nname: quoted\ndescription: "Does a thing, with commas."\n---\n',
    )
    report = validate_skill(skill)
    assert report.ok, report.problems
    assert report.description == "Does a thing, with commas."


def test_validate_accepts_skill_md_path_directly() -> None:
    report = validate_skill(SKILLS_DIR / "lead-list-checker" / "SKILL.md")
    assert report.ok, report.problems
