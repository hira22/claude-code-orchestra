"""Direct unit tests for .claude/hooks/lib/cli_logger.py.

The log path is redirected to a tmp file via $CLAUDE_CLI_LOG_FILE so tests
stay isolated and never touch the developer's session log.
"""

from __future__ import annotations

import importlib
import json
import sys

import pytest


@pytest.fixture
def cli_logger(lib_module_path, tmp_path, monkeypatch):
    log_file = tmp_path / "cli-tools.jsonl"
    monkeypatch.setenv("CLAUDE_CLI_LOG_FILE", str(log_file))
    if "lib.cli_logger" in sys.modules:
        mod = importlib.reload(sys.modules["lib.cli_logger"])
    else:
        mod = importlib.import_module("lib.cli_logger")
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


def test_agy_command_extraction(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_agy_prompt('agy -p "summarize this"') == "summarize this"
    assert (
        mod.extract_agy_prompt("agy -p 'transcribe @audio.mp3'")
        == "transcribe @audio.mp3"
    )
    assert mod.extract_agy_prompt("agy --version") is None


def test_extract_model_flag(cli_logger):
    mod, _ = cli_logger
    assert mod.extract_model("codex --model gpt-5 'foo'") == "gpt-5"
    assert mod.extract_model("codex 'foo'") is None


def test_extract_model_supports_equals_form(cli_logger):
    """agy accepts ``--model=NAME`` in addition to space-separated form."""
    mod, _ = cli_logger
    assert mod.extract_model("agy --model=gemini-3.1-pro -p 'x'") == "gemini-3.1-pro"


def test_extract_model_supports_quoted_display_names(cli_logger):
    """agy models like ``Gemini 3.5 Flash`` contain spaces; must not truncate."""
    mod, _ = cli_logger
    assert (
        mod.extract_model('agy --model="Gemini 3.5 Flash" -p "x"') == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model('agy --model "Gemini 3.5 Flash" -p "x"') == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model("agy --model='Gemini 3.5 Flash' -p 'x'") == "Gemini 3.5 Flash"
    )
    assert (
        mod.extract_model("agy --model 'Gemini 3.5 Flash' -p 'x'") == "Gemini 3.5 Flash"
    )


def test_detect_tool_classifies_by_binary_not_prompt_body(cli_logger):
    """``agy -p "... codex ..."`` must be classified as agy, not codex.

    Regression: prior substring-based detection routed such commands into
    the codex branch, which then failed to extract a prompt and dropped
    the log entry entirely.
    """
    mod, _ = cli_logger
    assert (
        mod.detect_tool('agy -p "analyze this codex error screenshot @err.png"')
        == "agy"
    )
    assert mod.detect_tool('codex exec "explain agy usage"') == "codex"
    assert mod.detect_tool("ls -la") is None
    # Env-var prefix should not fool the classifier.
    assert mod.detect_tool('FOO=bar agy -p "hi"') == "agy"


def test_check_logs_agy_when_prompt_mentions_codex(cli_logger):
    """End-to-end: an agy call whose prompt mentions ``codex`` is logged as agy."""
    mod, log_file = cli_logger
    payload = _bash(
        'agy -p "analyze this codex error screenshot @err.png"',
        stdout="Error is a KeyError on line 42.",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "analyze this codex error screenshot @err.png"


def test_check_writes_agy_entry_with_quoted_model_display_name(cli_logger):
    """``--model="Gemini 3.5 Flash"`` is recorded verbatim, quotes stripped."""
    mod, log_file = cli_logger
    payload = _bash(
        'agy --model="Gemini 3.5 Flash" -p "describe @img.png"',
        stdout="A cat.",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["model"] == "Gemini 3.5 Flash"


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


def test_check_writes_agy_entry(cli_logger):
    mod, log_file = cli_logger
    payload = _bash('agy -p "describe @img.png"', stdout="A cat", exit_code=0)
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["prompt"] == "describe @img.png"
    # Model label defaults to the tool name; --model overrides record the flag.
    assert entry["model"] == "agy"


def test_check_writes_agy_entry_with_model_flag(cli_logger):
    mod, log_file = cli_logger
    payload = _bash(
        "agy --model gemini-3.1-pro -p 'read @doc.pdf'",
        stdout="Doc content",
        exit_code=0,
    )
    result = mod.check(payload)
    assert result is not None
    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "agy"
    assert entry["model"] == "gemini-3.1-pro"


def test_check_appends_multiple_entries(cli_logger):
    mod, log_file = cli_logger
    mod.check(_bash('codex exec "first"', stdout="a"))
    mod.check(_bash('codex exec "second"', stdout="b"))
    mod.check(_bash('codex exec "third"', stdout="c"))
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    prompts = [json.loads(line)["prompt"] for line in lines]
    assert prompts == ["first", "second", "third"]


def test_non_codex_agy_command_skipped(cli_logger):
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
