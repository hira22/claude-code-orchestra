"""Detect errors in Bash command output and suggest codex-debugger.

Pure-logic module imported by bash-postdispatch.py. Regex patterns are
pre-compiled at module load to avoid per-call compile overhead.
"""

import re

_RAW_ERROR_PATTERNS = [
    r"Traceback \(most recent call last\)",
    r"(?:Error|Exception):\s+\S",
    r"error\[\w+\]",
    r"panic:",
    r"FAIL[ED:\s]",
    r"fatal:",
    r"segmentation fault",
    r"core dumped",
    r"(?:Cannot|Could not|Unable to)\s",
    r"(?:TypeError|ValueError|AttributeError|ImportError|KeyError|IndexError|RuntimeError)",
    r"(?:SyntaxError|NameError|FileNotFoundError|PermissionError|OSError)",
    r"npm ERR!",
    r"cargo error",
]

ERROR_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RAW_ERROR_PATTERNS]

IGNORE_COMMANDS = [
    "git status",
    "git log",
    "git diff",
    "git branch",
    "ls",
    "pwd",
    "cat",
    "head",
    "tail",
    "echo",
    "which",
    "type",
    "true",
    "grep",
    "find",
]

IGNORE_OUTPUTS = [
    "command not found",
    "No such file or directory",
    "already exists",
    "nothing to commit",
    "Already up to date",
    "Everything up-to-date",
]

SKIP_COMMANDS = [
    "codex ",
    "agy ",
]

MIN_OUTPUT_LENGTH = 20


def _should_ignore_command(command: str) -> bool:
    command_stripped = command.strip()
    for ignore in IGNORE_COMMANDS:
        if command_stripped.startswith(ignore):
            return True
    for skip in SKIP_COMMANDS:
        if skip in command_stripped:
            return True
    return False


def _should_ignore_output(output: str) -> bool:
    for ignore in IGNORE_OUTPUTS:
        if ignore in output and output.count("\n") < 5:
            return True
    return False


def _detect_errors(output: str) -> list[str]:
    return [p.pattern for p in ERROR_PATTERNS if p.search(output)]


def check(data: dict) -> dict | None:
    """Return a hookSpecificOutput dict if errors are detected, else None."""
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    command = tool_input.get("command", "")
    tool_output = tool_response.get("stdout", "") or tool_response.get("content", "")

    # `exit_code` may be missing from the payload; only short-circuit when
    # the field is *explicitly* present and zero.
    exit_code = tool_response.get("exit_code")
    if exit_code == 0:
        return None

    if not command or not tool_output:
        return None

    if len(tool_output) < MIN_OUTPUT_LENGTH:
        return None

    if _should_ignore_command(command):
        return None

    if _should_ignore_output(tool_output):
        return None

    errors = _detect_errors(tool_output)
    if not errors:
        return None

    return {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            f"[Error Detected] {len(errors)} error pattern(s) found in command output. "
            "**Action**: Use the `codex-debugger` subagent to analyze this error. "
            "Pass the full command and error output to the subagent for Codex-powered diagnosis. "
            "Example: Task(subagent_type='codex-debugger', prompt='Analyze this error: ...')"
        ),
    }
