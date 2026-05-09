"""Unit tests for .claude/hooks/log-cli-tools.py (TaskCompleted hook).

The hook writes to .claude/logs/cli-tools.jsonl (gitignored). Tests assert that
the last appended line matches the expected JSON structure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HOOK = "log-cli-tools.py"


@pytest.fixture
def log_file(project_root: Path) -> Path:
    return project_root / ".claude" / "logs" / "cli-tools.jsonl"


def _bash(command: str, stdout: str = "", exit_code: int = 0) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "exit_code": exit_code},
    }


def _last_line(log_file: Path) -> dict | None:
    if not log_file.exists():
        return None
    lines = log_file.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1]) if lines else None


def _line_count(log_file: Path) -> int:
    if not log_file.exists():
        return 0
    return sum(1 for _ in log_file.read_text(encoding="utf-8").splitlines())


def test_non_bash_tool_skipped(hook_runner, log_file: Path):
    before = _line_count(log_file)
    result = hook_runner(HOOK, {"tool_name": "Read", "tool_input": {}})
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert _line_count(log_file) == before, "No log entry expected for non-Bash"


def test_non_codex_gemini_command_skipped(hook_runner, log_file: Path):
    before = _line_count(log_file)
    result = hook_runner(HOOK, _bash("ls -la"))
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert _line_count(log_file) == before


def test_codex_command_logs_entry(hook_runner, log_file: Path):
    before = _line_count(log_file)
    payload = _bash(
        command='codex exec --sandbox read-only "Explain prime factorization"',
        stdout="Prime factorization is...",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert "[LOG]" in result.stdout
    assert _line_count(log_file) == before + 1
    entry = _last_line(log_file)
    assert entry["tool"] == "codex"
    assert "Explain prime factorization" in entry["prompt"]
    assert entry["success"] is True


def test_gemini_command_logs_entry(hook_runner, log_file: Path):
    before = _line_count(log_file)
    payload = _bash(
        command='gemini -p "describe this image @photo.png"',
        stdout="A cat sitting on a chair.",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert _line_count(log_file) == before + 1
    entry = _last_line(log_file)
    assert entry["tool"] == "gemini"
    assert "describe this image" in entry["prompt"]


def test_codex_without_extractable_prompt_not_logged(hook_runner, log_file: Path):
    """No quoted prompt → cannot extract → skip logging."""
    before = _line_count(log_file)
    payload = _bash(command="codex --version", stdout="codex 0.1", exit_code=0)
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert _line_count(log_file) == before
