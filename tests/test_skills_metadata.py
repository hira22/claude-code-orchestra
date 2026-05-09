"""Validate every .claude/skills/*/SKILL.md frontmatter is well-formed."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

EXPECTED_SKILL_COUNT = 17
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _load_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    assert match, f"{skill_md}: missing YAML frontmatter (expected leading ---)"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict), f"{skill_md}: frontmatter must parse to a mapping"
    return parsed


@pytest.fixture(scope="module")
def skill_dirs(skills_dir: Path) -> list[Path]:
    return sorted(d for d in skills_dir.iterdir() if d.is_dir())


def test_expected_skill_count_after_pr2_merge(skill_dirs: list[Path]):
    """PR #2 merged update-design into design-tracker (18 → 17)."""
    names = sorted(d.name for d in skill_dirs)
    assert len(skill_dirs) == EXPECTED_SKILL_COUNT, (
        f"Expected {EXPECTED_SKILL_COUNT} skills after PR #2, got {len(skill_dirs)}: {names}"
    )
    assert "update-design" not in names, "update-design should be merged into design-tracker"
    assert "design-tracker" in names


def test_every_skill_has_skill_md(skill_dirs: list[Path]):
    missing = [d.name for d in skill_dirs if not (d / "SKILL.md").exists()]
    assert not missing, f"Skill dirs missing SKILL.md: {missing}"


def test_every_skill_md_has_required_frontmatter_keys(skill_dirs: list[Path]):
    for skill_dir in skill_dirs:
        meta = _load_frontmatter(skill_dir / "SKILL.md")
        assert "name" in meta, f"{skill_dir.name}: missing 'name' in frontmatter"
        assert "description" in meta, f"{skill_dir.name}: missing 'description' in frontmatter"
        assert isinstance(meta["name"], str) and meta["name"].strip()
        assert isinstance(meta["description"], str) and meta["description"].strip()


def test_skill_name_matches_directory_name(skill_dirs: list[Path]):
    mismatches: list[tuple[str, str]] = []
    for skill_dir in skill_dirs:
        meta = _load_frontmatter(skill_dir / "SKILL.md")
        if meta["name"] != skill_dir.name:
            mismatches.append((skill_dir.name, meta["name"]))
    assert not mismatches, f"Skill name != directory name: {mismatches}"


def test_skill_names_are_unique(skill_dirs: list[Path]):
    names = [_load_frontmatter(d / "SKILL.md")["name"] for d in skill_dirs]
    duplicates = [name for name, count in Counter(names).items() if count > 1]
    assert not duplicates, f"Duplicate skill names: {duplicates}"


def test_skill_description_under_reasonable_length(skill_dirs: list[Path]):
    """Auto-invoke descriptions should stay short (PR #2 trimmed to ~80 chars)."""
    too_long: list[tuple[str, int]] = []
    for skill_dir in skill_dirs:
        meta = _load_frontmatter(skill_dir / "SKILL.md")
        desc = meta["description"]
        if len(desc) > 1024:
            too_long.append((skill_dir.name, len(desc)))
    assert not too_long, f"Skill descriptions exceed 1024 chars: {too_long}"


def test_referenced_files_in_skill_md_exist(skill_dirs: list[Path]):
    """Validate that local references/*.md links inside SKILL.md actually exist."""
    ref_pattern = re.compile(r"references/[\w./-]+\.md")
    broken: list[tuple[str, str]] = []
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")
        for match in ref_pattern.finditer(text):
            ref_path = skill_dir / match.group(0)
            if not ref_path.exists():
                broken.append((skill_dir.name, match.group(0)))
    assert not broken, f"Broken references/*.md links: {broken}"
