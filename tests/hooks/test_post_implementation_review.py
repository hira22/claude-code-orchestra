"""Unit tests for .claude/hooks/post-implementation-review.py (PostToolUse:Edit|Write).

The hook persists state to /tmp/claude-code-implementation-state.json by
default; tests redirect it to a per-test tmp file via
$CLAUDE_IMPLEMENTATION_STATE_FILE so they do not unlink an active session's
review-suggestion bookkeeping.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HOOK = "post-implementation-review.py"


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "implementation-state.json"


@pytest.fixture
def hook_env(state_file: Path) -> dict[str, str]:
    return {"CLAUDE_IMPLEMENTATION_STATE_FILE": str(state_file)}


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    return json.loads(stdout) if stdout else None


def _payload(file_path: str, content: str = "x = 1") -> dict:
    return {
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
    }


def test_non_write_edit_tool_skipped(hook_runner, hook_env, state_file: Path):
    result = hook_runner(HOOK, {"tool_name": "Bash", "tool_input": {}}, env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert not state_file.exists()


def test_non_source_file_skipped(hook_runner, hook_env, state_file: Path):
    result = hook_runner(HOOK, _payload("README.md", "# hi"), env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    # State should not be touched for non-source files (validates early-skip path).
    assert not state_file.exists()


def test_three_files_triggers_review_suggestion(hook_runner, hook_env):
    for i in range(2):
        result = hook_runner(HOOK, _payload(f"src/file_{i}.py", "x = 1"), env=hook_env)
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            "First two edits should not yet suggest review"
        )

    result = hook_runner(HOOK, _payload("src/file_2.py", "x = 1"), env=hook_env)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Code Review Suggestion" in ctx
    assert "files modified" in ctx


def test_review_only_suggested_once_per_session(hook_runner, hook_env):
    """Once review_suggested=True, subsequent edits short-circuit (PR #2 perf fix)."""
    for i in range(3):
        hook_runner(HOOK, _payload(f"src/file_{i}.py"), env=hook_env)

    # Now state should be: review_suggested=True. Next edit must NOT re-suggest.
    result = hook_runner(HOOK, _payload("src/file_extra.py"), env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == "", "Review suggestion must only fire once"


def test_path_traversal_silently_skipped(hook_runner, hook_env, state_file: Path):
    result = hook_runner(HOOK, _payload("../../etc/passwd.py"), env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert not state_file.exists()
