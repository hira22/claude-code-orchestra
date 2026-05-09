"""Direct unit tests for .claude/hooks/lib/error_detector.py."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture(scope="module")
def error_detector(lib_module_path):
    if "lib.error_detector" in sys.modules:
        return importlib.reload(sys.modules["lib.error_detector"])
    return importlib.import_module("lib.error_detector")


def _payload(command: str, stdout: str, exit_code: int = 1) -> dict:
    return {
        "tool_input": {"command": command},
        "tool_response": {"stdout": stdout, "exit_code": exit_code},
    }


def test_detects_python_traceback(error_detector):
    output = "Traceback (most recent call last):\n  File 'a.py', line 1\nValueError: bad"
    result = error_detector.check(_payload("python a.py", output))
    assert result is not None
    assert "Error Detected" in result["additionalContext"]


def test_detects_npm_err(error_detector):
    output = "npm ERR! something broke real bad here\nmore lines\nyet more"
    result = error_detector.check(_payload("npm install", output))
    assert result is not None


def test_ignores_clean_command(error_detector):
    result = error_detector.check(_payload("ls", "file1\nfile2", exit_code=0))
    assert result is None


def test_ignores_git_status(error_detector):
    output = "On branch main\nfatal: just kidding, this is fine actually"
    result = error_detector.check(_payload("git status", output, exit_code=0))
    assert result is None


def test_short_output_skipped(error_detector):
    result = error_detector.check(_payload("python a.py", "Error: x", exit_code=1))
    assert result is None  # Below MIN_OUTPUT_LENGTH (20)


def test_codex_command_skipped(error_detector):
    long_error = "Error: something went very wrong indeed " * 5
    result = error_detector.check(_payload("codex exec 'foo'", long_error, exit_code=1))
    assert result is None


def test_explicit_zero_exit_skipped(error_detector):
    long_error = "Error: this looks bad but exit_code says fine " * 3
    result = error_detector.check(_payload("python a.py", long_error, exit_code=0))
    assert result is None


def test_missing_exit_code_still_detects(error_detector):
    """Per the docstring, exit_code missing should NOT short-circuit."""
    output = "Traceback (most recent call last):\n  AssertionError: x\n  more lines\n"
    payload = {
        "tool_input": {"command": "python a.py"},
        "tool_response": {"stdout": output},  # no exit_code
    }
    result = error_detector.check(payload)
    assert result is not None


def test_empty_command_returns_none(error_detector):
    result = error_detector.check(_payload("", "Error: bad" * 10, exit_code=1))
    assert result is None


def test_ignored_output_skipped(error_detector):
    result = error_detector.check(
        _payload("npm install", "npm ERR! command not found", exit_code=1)
    )
    # IGNORE_OUTPUTS catches "command not found" → skip
    assert result is None
