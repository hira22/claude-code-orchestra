#!/usr/bin/env python3
"""
PostToolUse hook: Log Codex/Gemini CLI input/output to JSONL file.

Triggers after Bash tool calls containing 'codex' or 'gemini' commands.
Logs are stored in .claude/logs/cli-tools.jsonl

All agents (Claude Code, subagents, Codex, Gemini) can read this log.
"""

import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_LOG_FILE = Path(__file__).parent.parent / "logs" / "cli-tools.jsonl"


def _resolve_log_file() -> Path:
    override = os.environ.get("CLAUDE_CLI_LOG_FILE")
    return Path(override) if override else DEFAULT_LOG_FILE


def extract_codex_prompt(command: str) -> str | None:
    """Extract prompt from a `codex exec` command.

    Returns the longest quoted string found after `codex exec`. The prompt is
    almost always significantly longer than any flag value (e.g. legacy forms
    such as `--config model_reasoning_effort="high"` precede the real prompt),
    so picking the longest quoted segment correctly skips quoted flag values
    while remaining robust to multi-line, backslash-continued commands.
    """
    anchor = re.search(r"codex\s+exec\b", command)
    if not anchor:
        return None
    rest = command[anchor.end() :]
    candidates = re.findall(r'"([^"]+)"', rest)
    candidates += re.findall(r"'([^']+)'", rest)
    if not candidates:
        return None
    return max(candidates, key=len).strip()


def extract_gemini_prompt(command: str) -> str | None:
    """Extract prompt from gemini command."""
    # Pattern: gemini -p "prompt" or gemini -p 'prompt'
    patterns = [
        r'gemini\s+-p\s+"([^"]+)"',
        r"gemini\s+-p\s+'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def extract_model(command: str) -> str | None:
    """Extract model name from command."""
    match = re.search(r"--model\s+(\S+)", command)
    return match.group(1) if match else None


def truncate_text(text: str, max_length: int = 2000) -> str:
    """Truncate text if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"... [truncated, {len(text)} total chars]"


def log_entry(entry: dict) -> None:
    """Append entry to JSONL log file."""
    log_file = _resolve_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    # Only process Bash tool calls
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Bash":
        return

    # Get command and output
    tool_input = hook_input.get("tool_input", {})
    tool_response = hook_input.get("tool_response", {})

    command = tool_input.get("command", "")
    output = tool_response.get("stdout", "") or tool_response.get("content", "")

    # Check if this is a codex or gemini command
    is_codex = "codex" in command.lower()
    is_gemini = "gemini" in command.lower() and "codex" not in command.lower()

    if not (is_codex or is_gemini):
        return

    # Extract prompt based on tool type
    if is_codex:
        tool = "codex"
        prompt = extract_codex_prompt(command)
        model = extract_model(command) or "default"
    else:
        tool = "gemini"
        prompt = extract_gemini_prompt(command)
        model = "gemini-3.1-pro-preview"

    if not prompt:
        # Could not extract prompt, skip logging
        return

    # Determine success
    exit_code = tool_response.get("exit_code", 0)
    success = exit_code == 0 and bool(output)

    # Create log entry
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": tool,
        "model": model,
        "prompt": truncate_text(prompt),
        "response": truncate_text(output) if output else "",
        "success": success,
        "exit_code": exit_code,
    }

    log_entry(entry)

    # Output notification via hookSpecificOutput
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "additionalContext": f"[LOG] {tool.capitalize()} call logged to .claude/logs/cli-tools.jsonl",
                }
            }
        )
    )


if __name__ == "__main__":
    main()
