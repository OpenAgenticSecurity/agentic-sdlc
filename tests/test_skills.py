from __future__ import annotations

from pathlib import Path
import re

import yaml


REPO = Path(__file__).resolve().parents[1]
SKILL_FILES = sorted((REPO / "skills").glob("*/SKILL.md"))
SKILL_NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path}: missing YAML frontmatter"
    raw, closing, _body = text[4:].partition("\n---\n")
    assert closing, f"{path}: unterminated YAML frontmatter"
    assert len(raw) <= 1024, f"{path}: frontmatter exceeds 1024 characters ({len(raw)})"
    # Skill installers (`npx skills add`, Claude Code, Cursor, Codex) parse this
    # block as strict YAML and silently skip a skill whose frontmatter fails.
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict), f"{path}: frontmatter must be a YAML mapping"
    return parsed


def test_skill_files_are_discovered() -> None:
    assert len(SKILL_FILES) == 6, [p.parent.name for p in SKILL_FILES]


def test_skill_frontmatter_is_strict_yaml_with_matching_name() -> None:
    for path in SKILL_FILES:
        meta = _frontmatter(path)
        assert set(meta) == {"name", "description"}, f"{path}: unexpected frontmatter keys {sorted(meta)}"
        name = meta["name"]
        assert isinstance(name, str) and SKILL_NAME_RE.fullmatch(name), f"{path}: invalid skill name {name!r}"
        assert name == path.parent.name, f"{path}: name {name!r} must equal its directory name"
        description = meta["description"]
        assert isinstance(description, str) and description.strip(), f"{path}: description must be non-empty text"


def test_skill_descriptions_state_when_to_use() -> None:
    for path in SKILL_FILES:
        description = _frontmatter(path)["description"]
        assert isinstance(description, str)
        assert description.startswith("Use when "), (
            f"{path}: description must open with the trigger condition ('Use when ...'), got {description[:60]!r}"
        )
        assert "\n" not in description.strip(), f"{path}: description must be a single line"
        assert len(description) <= 500, f"{path}: description is {len(description)} characters (limit 500)"
