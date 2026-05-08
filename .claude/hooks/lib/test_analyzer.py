"""Suggest Codex consultation after complex test/build failures.

Pure-logic module imported by bash-postdispatch.py.
"""

import re

TEST_BUILD_COMMANDS = [
    "pytest",
    "npm test",
    "npm run test",
    "npm run build",
    "uv run pytest",
    "ruff check",
    "ty check",
    "mypy",
    "tsc",
    "cargo test",
    "go test",
    "make test",
    "make build",
]

_RAW_FAILURE_PATTERNS = [
    r"FAILED",
    r"ERROR",
    r"error\[",
    r"Error:",
    r"failed",
    r"error:",
    r"AssertionError",
    r"TypeError",
    r"ValueError",
    r"AttributeError",
    r"ImportError",
    r"ModuleNotFoundError",
    r"SyntaxError",
    r"Exception",
    r"Traceback",
    r"panic:",
    r"FAIL:",
]

FAILURE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RAW_FAILURE_PATTERNS]

SIMPLE_ERRORS = [
    "ModuleNotFoundError",
    "command not found",
    "No such file or directory",
]


def _is_test_or_build_command(command: str) -> bool:
    command_lower = command.lower()
    return any(cmd in command_lower for cmd in TEST_BUILD_COMMANDS)


def _has_complex_failure(output: str) -> tuple[bool, str]:
    for simple in SIMPLE_ERRORS:
        if simple in output:
            return False, ""

    failure_count = 0
    for pattern in FAILURE_PATTERNS:
        matches = pattern.findall(output)
        failure_count += len(matches)

    if failure_count >= 3:
        return True, f"Multiple failures detected ({failure_count} issues)"

    if failure_count >= 1 and any(p in output.lower() for p in ["traceback", "assertion"]):
        return True, "Test failure with traceback"

    return False, ""


def check(data: dict) -> dict | None:
    """Return a hookSpecificOutput dict if a complex failure is detected, else None."""
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    command = tool_input.get("command", "")
    tool_output = tool_response.get("stdout", "") or tool_response.get("content", "")

    if not _is_test_or_build_command(command):
        return None

    has_failure, reason = _has_complex_failure(tool_output)
    if not has_failure:
        return None

    return {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"[Codex Debug Suggestion] {reason}. "
            "Consider consulting Codex for debugging analysis. "
            "**Recommended**: Use Task tool with subagent_type='general-purpose' "
            "to consult Codex with full error context and preserve main context."
        ),
    }
