"""Unit tests for .claude/hooks/post-implementation-review.py (PostToolUse:Edit|Write).

The hook persists state to /tmp/claude-code-implementation-state.json. Each test
resets that file so runs are deterministic regardless of order or prior sessions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HOOK = "post-implementation-review.py"
STATE_FILE = Path("/tmp/claude-code-implementation-state.json")


@pytest.fixture(autouse=True)
def reset_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    yield
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    return json.loads(stdout) if stdout else None


def _payload(file_path: str, content: str = "x = 1") -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
    }


def test_non_write_edit_tool_skipped(hook_runner):
    result = hook_runner(HOOK, {"tool_name": "Bash", "tool_input": {}})
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert not STATE_FILE.exists()


def test_non_source_file_skipped(hook_runner):
    result = hook_runner(HOOK, _payload("README.md", "# hi"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    # State should not be touched for non-source files (validates early-skip path).
    assert not STATE_FILE.exists()


def test_three_files_triggers_review_suggestion(hook_runner):
    for i in range(2):
        result = hook_runner(HOOK, _payload(f"src/file_{i}.py", "x = 1"))
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            "First two edits should not yet suggest review"
        )

    result = hook_runner(HOOK, _payload("src/file_2.py", "x = 1"))
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Code Review Suggestion" in ctx
    assert "files modified" in ctx


def test_review_only_suggested_once_per_session(hook_runner):
    """Once review_suggested=True, subsequent edits short-circuit (PR #2 perf fix)."""
    for i in range(3):
        hook_runner(HOOK, _payload(f"src/file_{i}.py"))

    # Now state should be: review_suggested=True. Next edit must NOT re-suggest.
    result = hook_runner(HOOK, _payload("src/file_extra.py"))
    assert result.returncode == 0
    assert result.stdout.strip() == "", "Review suggestion must only fire once"


def test_path_traversal_silently_skipped(hook_runner):
    result = hook_runner(HOOK, _payload("../../etc/passwd.py"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert not STATE_FILE.exists()
