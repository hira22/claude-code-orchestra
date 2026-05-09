"""Log Codex/Gemini CLI input/output to .claude/logs/cli-tools.jsonl.

Extracted from log-cli-tools.py so the same logic is reused by the
PostToolUse:Bash dispatcher.

The log path is resolved per call: $CLAUDE_CLI_LOG_FILE wins, falling back
to the project-relative default. Tests set the env var to a tmp path so
they do not pollute the developer's session log.
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_LOG_FILE = (
    Path(__file__).resolve().parent.parent.parent / "logs" / "cli-tools.jsonl"
)


def _resolve_log_file() -> Path:
    override = os.environ.get("CLAUDE_CLI_LOG_FILE")
    return Path(override) if override else DEFAULT_LOG_FILE


def extract_codex_prompt(command: str) -> str | None:
    """Extract prompt from a `codex exec` command (longest quoted segment after the anchor)."""
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
    match = re.search(r"--model\s+(\S+)", command)
    return match.group(1) if match else None


def truncate_text(text: str, max_length: int = 2000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + f"... [truncated, {len(text)} total chars]"


def _log_entry(entry: dict) -> None:
    log_file = _resolve_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def check(data: dict) -> dict | None:
    """Log a Codex/Gemini call if the command matches; return notification dict or None."""
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})

    command = tool_input.get("command", "")
    output = tool_response.get("stdout", "") or tool_response.get("content", "")

    is_codex = "codex" in command.lower()
    is_gemini = "gemini" in command.lower() and "codex" not in command.lower()

    if not (is_codex or is_gemini):
        return None

    if is_codex:
        tool = "codex"
        prompt = extract_codex_prompt(command)
        model = extract_model(command) or "default"
    else:
        tool = "gemini"
        prompt = extract_gemini_prompt(command)
        model = "gemini-3.1-pro-preview"

    if not prompt:
        return None

    exit_code = tool_response.get("exit_code", 0)
    success = exit_code == 0 and bool(output)

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "tool": tool,
        "model": model,
        "prompt": truncate_text(prompt),
        "response": truncate_text(output) if output else "",
        "success": success,
        "exit_code": exit_code,
    }

    _log_entry(entry)

    return {
        "additionalContext": f"[LOG] {tool.capitalize()} call logged to .claude/logs/cli-tools.jsonl",
    }
