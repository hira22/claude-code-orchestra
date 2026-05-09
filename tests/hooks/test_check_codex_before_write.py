"""Unit tests for .claude/hooks/check-codex-before-write.py (PreToolUse:Edit|Write)."""

from __future__ import annotations

import json


HOOK = "check-codex-before-write.py"


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    return json.loads(stdout) if stdout else None


def _payload(file_path: str, content: str = "") -> dict:
    return {"tool_input": {"file_path": file_path, "content": content}}


def test_simple_edit_pattern_skipped(hook_runner):
    """README.md is in SIMPLE_EDIT_PATTERNS → no suggestion."""
    result = hook_runner(HOOK, _payload("docs/README.md", "# Hello"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_design_indicator_in_path_triggers_suggestion(hook_runner):
    result = hook_runner(HOOK, _payload("src/architecture/core.py", "x=1"))
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
    assert "Codex Consultation Reminder" in out["hookSpecificOutput"]["additionalContext"]


def test_path_traversal_silently_skipped(hook_runner):
    result = hook_runner(HOOK, _payload("../etc/passwd"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_neutral_small_file_not_suggested(hook_runner):
    result = hook_runner(HOOK, _payload("src/utils.py", "print('hi')"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_invalid_json_does_not_crash(hook_runner):
    result = hook_runner(HOOK, "{{{ broken")
    assert result.returncode == 0
    assert "Hook error" in result.stderr or result.stderr == ""
