#!/usr/bin/env python3
"""
PostToolUse hook: Log Codex/agy CLI input/output to JSONL file.

Triggers after Bash tool calls containing 'codex' or 'agy' commands.
Logs are stored in .claude/logs/cli-tools.jsonl

All agents (Claude Code, subagents, Codex, agy) can read this log.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Reuse the shared classification/extraction helpers from lib.cli_logger so
# behaviour stays in lockstep with the PostToolUse:Bash dispatcher.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.cli_logger import (  # noqa: E402
    detect_tool,
    extract_agy_prompt,
    extract_codex_prompt,
    extract_model,
    recover_agy_output,
    truncate_text,
)

DEFAULT_LOG_FILE = Path(__file__).parent.parent / "logs" / "cli-tools.jsonl"


def _resolve_log_file() -> Path:
    override = os.environ.get("CLAUDE_CLI_LOG_FILE")
    return Path(override) if override else DEFAULT_LOG_FILE


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

    # Classify by the invoked binary (not by substring on the full command);
    # otherwise an agy prompt that mentions the word "codex" would be routed
    # into the codex branch and dropped.
    tool = detect_tool(command)
    if tool is None:
        return

    # Extract prompt based on tool type
    if tool == "codex":
        prompt = extract_codex_prompt(command)
        model = extract_model(command) or "default"
    else:
        prompt = extract_agy_prompt(command)
        # agy supports multiple models via `--model`; record the flag value
        # when present and fall back to the tool name for the default case.
        model = extract_model(command) or "agy"

    if not prompt:
        # Could not extract prompt, skip logging
        return

    exit_code = tool_response.get("exit_code", 0)

    # Non-TTY agy runs may exit 0 with empty stdout while the result went to
    # brain artifacts only; recover it so the consultation is not recorded as
    # a failed/empty one (see lib.cli_logger.recover_agy_output).
    recovered_from_brain = False
    stdout_empty = False
    if tool == "agy" and exit_code == 0 and not output:
        brain_output = recover_agy_output(prompt)
        if brain_output:
            output = brain_output
            recovered_from_brain = True
        else:
            stdout_empty = True

    # Determine success
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
    if recovered_from_brain:
        entry["recovered_from_brain"] = True
    if stdout_empty:
        # exit 0 + no output + no attributable brain run: outcome unknown,
        # not a confirmed failure — let downstream consumers tell them apart.
        entry["stdout_empty"] = True

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
