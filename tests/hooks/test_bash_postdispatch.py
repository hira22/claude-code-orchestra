"""Unit tests for .claude/hooks/bash-postdispatch.py (PostToolUse:Bash dispatcher).

Mirrors the test plan in PR #2:
- pytest failure payload  → all 3 handlers fire
- `git status` payload    → short-circuits, no handler context
- `codex exec` payload    → only cli_logger fires (and writes to logs)
- malformed JSON          → exit 0, no crash
- non-Bash tool payload   → exit 0, no output
"""

from __future__ import annotations

import json
from pathlib import Path

HOOK = "bash-postdispatch.py"


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def _bash_payload(command: str, stdout: str = "", exit_code: int = 0) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "exit_code": exit_code},
    }


PYTEST_FAILURE_OUTPUT = """\
============================= test session starts ==============================
collected 3 items

tests/test_a.py::test_one FAILED
tests/test_a.py::test_two FAILED
tests/test_b.py::test_three FAILED

=================================== FAILURES ===================================
______________________________ test_one ________________________________________
Traceback (most recent call last):
  File "tests/test_a.py", line 5, in test_one
    assert 1 == 2
AssertionError
========================= 3 failed, 0 passed in 0.12s ==========================
"""


def test_pytest_failure_triggers_error_and_test_handlers(hook_runner):
    payload = _bash_payload(
        command="uv run pytest -v",
        stdout=PYTEST_FAILURE_OUTPUT,
        exit_code=1,
    )
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = _parse(result.stdout)
    assert out is not None, "Expected dispatcher to emit context for pytest failure"
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Error Detected" in ctx, f"error_detector should fire: {ctx}"
    assert "Codex Debug Suggestion" in ctx, f"test_analyzer should fire: {ctx}"


def test_git_status_payload_short_circuits(hook_runner):
    payload = _bash_payload(
        command="git status",
        stdout="On branch main\nnothing to commit, working tree clean\n",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert result.stdout.strip() == "", (
        f"git status should not trigger any handler, got: {result.stdout!r}"
    )


def test_codex_payload_triggers_only_cli_logger(hook_runner, tmp_path: Path):
    """codex exec payload triggers cli_logger; error/test handlers skip codex commands."""
    payload = _bash_payload(
        command='codex exec --sandbox read-only "What is 2+2?"',
        stdout="The answer is 4.",
        exit_code=0,
    )
    log_file = tmp_path / "cli-tools.jsonl"

    result = hook_runner(HOOK, payload, env={"CLAUDE_CLI_LOG_FILE": str(log_file)})
    assert result.returncode == 0, f"stderr: {result.stderr}"
    out = _parse(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "[LOG]" in ctx and "Codex" in ctx
    assert "Error Detected" not in ctx
    assert "Codex Debug Suggestion" not in ctx

    # Verify the dispatcher routed to cli_logger and wrote a JSON line.
    assert log_file.exists(), "cli_logger should have appended a line to the tmp log"
    last_line = log_file.read_text(encoding="utf-8").splitlines()[-1]
    entry = json.loads(last_line)
    assert entry["tool"] == "codex"
    assert "What is 2+2?" in entry["prompt"]


def test_non_bash_tool_payload_emits_nothing(hook_runner):
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/foo"},
        "tool_response": {"content": "hello"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_invalid_json_exits_clean(hook_runner):
    result = hook_runner(HOOK, "garbage{{{")
    assert result.returncode == 0
    assert result.stdout.strip() == ""
