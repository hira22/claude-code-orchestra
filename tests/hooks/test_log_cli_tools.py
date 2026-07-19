"""Unit tests for .claude/hooks/log-cli-tools.py (TaskCompleted hook).

The hook writes to .claude/logs/cli-tools.jsonl by default; tests redirect
it to a tmp file via $CLAUDE_CLI_LOG_FILE so they do not pollute the
developer's session log.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HOOK = "log-cli-tools.py"


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    return tmp_path / "cli-tools.jsonl"


@pytest.fixture
def hook_env(log_file: Path) -> dict[str, str]:
    return {"CLAUDE_CLI_LOG_FILE": str(log_file)}


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


def test_non_bash_tool_skipped(hook_runner, hook_env, log_file: Path):
    result = hook_runner(HOOK, {"tool_name": "Read", "tool_input": {}}, env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert _line_count(log_file) == 0, "No log entry expected for non-Bash"


def test_non_codex_agy_command_skipped(hook_runner, hook_env, log_file: Path):
    result = hook_runner(HOOK, _bash("ls -la"), env=hook_env)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert _line_count(log_file) == 0


def test_codex_command_logs_entry(hook_runner, hook_env, log_file: Path):
    payload = _bash(
        command='codex exec --sandbox read-only "Explain prime factorization"',
        stdout="Prime factorization is...",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    assert "[LOG]" in result.stdout
    assert _line_count(log_file) == 1
    entry = _last_line(log_file)
    assert entry["tool"] == "codex"
    assert "Explain prime factorization" in entry["prompt"]
    assert entry["success"] is True


def test_agy_command_logs_entry(hook_runner, hook_env, log_file: Path):
    payload = _bash(
        command='agy -p "describe this image @photo.png"',
        stdout="A cat sitting on a chair.",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    assert _line_count(log_file) == 1
    entry = _last_line(log_file)
    assert entry["tool"] == "agy"
    assert "describe this image" in entry["prompt"]
    # Model label defaults to the tool name; --model overrides record the flag.
    assert entry["model"] == "agy"


def test_agy_command_with_model_flag_records_model(
    hook_runner, hook_env, log_file: Path
):
    payload = _bash(
        command="agy --model gemini-3.1-pro -p 'analyze @doc.pdf'",
        stdout="Doc analysis...",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    entry = _last_line(log_file)
    assert entry["tool"] == "agy"
    assert entry["model"] == "gemini-3.1-pro"


def test_codex_without_extractable_prompt_not_logged(
    hook_runner, hook_env, log_file: Path
):
    """No quoted prompt → cannot extract → skip logging."""
    payload = _bash(command="codex --version", stdout="codex 0.1", exit_code=0)
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    assert _line_count(log_file) == 0


def test_agy_prompt_mentioning_codex_is_logged_as_agy(
    hook_runner, hook_env, log_file: Path
):
    """Regression: substring detection previously routed this to the codex branch.

    The command executes ``agy`` (not ``codex``); the word "codex" only
    appears inside the prompt body. The hook must classify by the invoked
    binary, extract the agy prompt, and record ``tool = "agy"``.
    """
    payload = _bash(
        command='agy -p "analyze this codex error screenshot @err.png"',
        stdout="Error snippet parsed.",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    assert _line_count(log_file) == 1
    entry = _last_line(log_file)
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "analyze this codex error screenshot @err.png"


def test_agy_empty_stdout_recovered_from_brain(
    hook_runner, hook_env, log_file: Path, tmp_path: Path
):
    """Non-TTY agy run (exit 0, empty stdout) recovers the brain artifact.

    The run dir mirrors the real Antigravity CLI layout: the transcript
    lives under ``.system_generated/logs/``, artifacts at the run root.
    """
    run_dir = tmp_path / "brain" / "run-a"
    logs_dir = run_dir / ".system_generated" / "logs"
    logs_dir.mkdir(parents=True)
    (logs_dir / "transcript.jsonl").write_text(
        json.dumps(
            {
                "source": "USER_EXPLICIT",
                "type": "USER_INPUT",
                "content": "<USER_REQUEST>\ndescribe @img.png\n</USER_REQUEST>",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "result.md").write_text("A cat on a chair.", encoding="utf-8")
    env = {**hook_env, "CLAUDE_AGY_BRAIN_DIR": str(tmp_path / "brain")}
    payload = _bash('agy -p "describe @img.png"', stdout="", exit_code=0)
    result = hook_runner(HOOK, payload, env=env)
    assert result.returncode == 0
    entry = _last_line(log_file)
    assert entry["success"] is True
    assert entry["response"] == "A cat on a chair."
    assert entry["recovered_from_brain"] is True


def test_agy_empty_stdout_without_brain_match_flagged(
    hook_runner, hook_env, log_file: Path, tmp_path: Path
):
    env = {**hook_env, "CLAUDE_AGY_BRAIN_DIR": str(tmp_path / "empty-brain")}
    payload = _bash('agy -p "describe @img.png"', stdout="", exit_code=0)
    result = hook_runner(HOOK, payload, env=env)
    assert result.returncode == 0
    entry = _last_line(log_file)
    assert entry["success"] is False
    assert entry["stdout_empty"] is True


def test_agy_with_quoted_model_display_name(hook_runner, hook_env, log_file: Path):
    """``--model="Gemini 3.5 Flash"`` records the full display name."""
    payload = _bash(
        command='agy --model="Gemini 3.5 Flash" -p "describe @img.png"',
        stdout="A cat.",
        exit_code=0,
    )
    result = hook_runner(HOOK, payload, env=hook_env)
    assert result.returncode == 0
    entry = _last_line(log_file)
    assert entry["tool"] == "agy"
    assert entry["model"] == "Gemini 3.5 Flash"
