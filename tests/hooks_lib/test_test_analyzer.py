"""Direct unit tests for .claude/hooks/lib/test_analyzer.py."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture(scope="module")
def test_analyzer(lib_module_path):
    if "lib.test_analyzer" in sys.modules:
        return importlib.reload(sys.modules["lib.test_analyzer"])
    return importlib.import_module("lib.test_analyzer")


def _payload(command: str, stdout: str) -> dict:
    return {"tool_input": {"command": command}, "tool_response": {"stdout": stdout}}


def test_non_test_command_skipped(test_analyzer):
    result = test_analyzer.check(_payload("ls", "FAILED something"))
    assert result is None


def test_pytest_with_traceback_triggers(test_analyzer):
    output = "FAILED test_foo\nTraceback (most recent call last):\n  AssertionError"
    result = test_analyzer.check(_payload("uv run pytest", output))
    assert result is not None
    assert "Codex Debug Suggestion" in result["additionalContext"]


def test_simple_module_not_found_error_skipped(test_analyzer):
    """SIMPLE_ERRORS like ModuleNotFoundError should NOT trigger Codex."""
    output = "ModuleNotFoundError: No module named 'foo'\nFAILED FAILED FAILED"
    result = test_analyzer.check(_payload("pytest", output))
    assert result is None


def test_npm_test_with_three_failures(test_analyzer):
    output = "FAIL: test1\nFAIL: test2\nERROR: test3\nrandom"
    result = test_analyzer.check(_payload("npm test", output))
    assert result is not None
    assert "Multiple failures" in result["additionalContext"]


def test_passing_pytest_run_skipped(test_analyzer):
    output = "5 passed in 0.5s"
    result = test_analyzer.check(_payload("pytest -v", output))
    assert result is None


def test_ruff_check_failure(test_analyzer):
    output = "Found 5 errors.\nerror[X]\nerror[Y]\nerror[Z]"
    result = test_analyzer.check(_payload("ruff check .", output))
    assert result is not None  # 3 failure pattern matches → triggers
