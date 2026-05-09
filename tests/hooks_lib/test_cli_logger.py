"""Direct unit tests for .claude/hooks/lib/cli_logger.py.

LOG_FILE is monkeypatched to tmp_path so tests stay isolated and fast.
"""

from __future__ import annotations

import importlib
import json
import sys

import pytest


@pytest.fixture
def cli_logger(lib_module_path, tmp_path, monkeypatch):
    if "lib.cli_logger" in sys.modules:
        mod = importlib.reload(sys.modules["lib.cli_logger"])
    else:
        mod = importlib.import_module("lib.cli_logger")
    log_file = tmp_path / "cli-tools.jsonl"
    monkeypatch.setattr(mod, "LOG_DIR", tmp_path)
    monkeypatch.setattr(mod, "LOG_FILE", log_file)
    monkeypatch.setattr(mod, "_log_dir_ensured", False)
    return mod, log_file


def _bash(command: str, stdout: str = "", exit_code: int = 0) -> dict:
    return {
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "exit_code": exit_code},
    }


def test_codex_command_extraction_picks_longest_quoted_segment(cli_logger):
    mod, log_file = cli_logger
    cmd = (
        'codex exec --config model_reasoning_effort="high" '
        '"This is the actual prompt that is much longer"'
    )
    prompt = mod.extract_codex_prompt(cmd)
    assert prompt == "This is the actual prompt that is much longer"


def test_gemini_command_extraction(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_gemini_prompt('gemini -p "summarize this"') == "summarize this"
    assert mod.extract_gemini_prompt("gemini -p 'transcribe @audio.mp3'") == "transcribe @audio.mp3"
    assert mod.extract_gemini_prompt("gemini --version") is None


def test_extract_model_flag(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_model("codex --model gpt-5 'foo'") == "gpt-5"
    assert mod.extract_model("codex 'foo'") is None


def test_truncate_text_preserves_short(cli_logger):
    mod, _ = cli_logger
    assert mod.truncate_text("hello", max_length=10) == "hello"


def test_truncate_text_truncates_long(cli_logger):
    mod, _ = cli_logger
    text = "x" * 3000
    truncated = mod.truncate_text(text, max_length=2000)
    assert truncated.startswith("x" * 2000)
    assert "truncated" in truncated
    assert "3000 total" in truncated


def test_check_writes_codex_entry(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('codex exec "Hello world"', stdout="Hi there", exit_code=0)
    result = mod.check(payload)
    assert result is not None
    assert "[LOG]" in result["additionalContext"]
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["tool"] == "codex"
    assert entry["prompt"] == "Hello world"
    assert entry["response"] == "Hi there"
    assert entry["success"] is True
    assert entry["exit_code"] == 0


def test_check_writes_gemini_entry(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('gemini -p "describe @img.png"', stdout="A cat", exit_code=0)
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "gemini"
    assert entry["prompt"] == "describe @img.png"


def test_check_appends_multiple_entries(cli_logger):
    mod, log_file = cli_logger
    mod.check(_bash('codex exec "first"', stdout="a"))
    mod.check(_bash('codex exec "second"', stdout="b"))
    mod.check(_bash('codex exec "third"', stdout="c"))
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    prompts = [json.loads(line)["prompt"] for line in lines]
    assert prompts == ["first", "second", "third"]


def test_non_codex_gemini_command_skipped(cli_logger):
    mod, log_file = cli_logger
    assert mod.check(_bash("ls -la", stdout="a\nb")) is None
    assert not log_file.exists() or log_file.read_text() == ""


def test_codex_without_quoted_prompt_skipped(cli_logger):
    mod, log_file = cli_logger
    assert mod.check(_bash("codex --version", stdout="0.1")) is None
    assert not log_file.exists() or log_file.read_text() == ""


def test_failure_marked_success_false(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('codex exec "boom"', stdout="", exit_code=1)
    mod.check(payload)
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["success"] is False
    assert entry["exit_code"] == 1
