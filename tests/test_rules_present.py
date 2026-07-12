"""Validate .claude/rules/*.md files exist, are non-empty, and have headings."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

EXPECTED_RULES = {
    "codex-delegation.md",
    "coding-principles.md",
    "dev-environment.md",
    "multimodal-delegation.md",
    "language.md",
    "model-selection.md",
    "security.md",
    "testing.md",
}


@pytest.fixture(scope="module")
def rule_files(rules_dir: Path) -> list[Path]:
    return sorted(rules_dir.glob("*.md"))


def test_expected_rule_files_present(rule_files: list[Path]):
    actual = {p.name for p in rule_files}
    missing = EXPECTED_RULES - actual
    assert not missing, f"Missing rule files: {missing}"


def test_each_rule_is_non_empty_and_has_heading(rule_files: list[Path]):
    for rule in rule_files:
        text = rule.read_text(encoding="utf-8").strip()
        assert text, f"{rule.name}: rule file is empty"
        first_line = text.splitlines()[0]
        assert first_line.startswith("# "), (
            f"{rule.name}: first line must be a top-level heading, got {first_line!r}"
        )


def _grep_rule_references(root: Path) -> set[str]:
    """Find every `.claude/rules/<name>.md` reference under the project.

    Skips gitignored runtime/generated directories (checkpoints, agent-team
    work logs, log files). Otherwise a stale historical note from a prior
    session referencing a renamed/removed rule would fail this test even
    though the tracked tree is consistent.
    """
    pattern = re.compile(r"\.claude/rules/([\w-]+\.md)")
    found: set[str] = set()
    skip_dirs = {
        ".git",
        "node_modules",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        "tests",
        # Runtime-generated, gitignored under .claude/
        "checkpoints",
        "agent-teams",
        "logs",
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix not in {".md", ".py", ".json", ".toml", ".yml", ".yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in pattern.finditer(text):
            found.add(match.group(1))
    return found


def test_no_dangling_rule_references(project_root: Path, rule_files: list[Path]):
    referenced = _grep_rule_references(project_root)
    available = {p.name for p in rule_files}
    dangling = referenced - available
    assert not dangling, (
        f"References to non-existent rules: {dangling}. Available: {available}"
    )
