"""Log Codex/agy CLI input/output to .claude/logs/cli-tools.jsonl.

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

DEFAULT_BRAIN_DIR = Path.home() / ".gemini" / "antigravity-cli" / "brain"

# brain/ is global and accumulates runs from every project; only the most
# recent runs can belong to the call being logged.
MAX_BRAIN_RUNS_SCANNED = 10


def _resolve_log_file() -> Path:
    override = os.environ.get("CLAUDE_CLI_LOG_FILE")
    return Path(override) if override else DEFAULT_LOG_FILE


def _resolve_brain_dir() -> Path:
    override = os.environ.get("CLAUDE_AGY_BRAIN_DIR")
    return Path(override) if override else DEFAULT_BRAIN_DIR


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


def extract_agy_prompt(command: str) -> str | None:
    """Extract prompt from an `agy` command.

    Accepts the short flag `-p` and its documented long aliases `--print`
    and `--prompt`, with either quote style and either a space or `=`
    separator (e.g. `agy --print "..."`, `agy --prompt='...'`), plus
    intermediate flags such as `agy --model gemini-3.1-pro -p "..."`.
    Anchors on the `agy` token so unrelated `-p` flags in other commands
    do not match.
    """
    anchor = re.search(r"\bagy\b", command)
    if not anchor:
        return None
    rest = command[anchor.end() :]
    patterns = [
        r'(?:--print|--prompt|-p)(?:\s+|=)"([^"]+)"',
        r"(?:--print|--prompt|-p)(?:\s+|=)'([^']+)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, rest, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def extract_model(command: str) -> str | None:
    """Extract the `--model` argument value.

    Accepts all common forms:
    - ``--model gemini-3.1-pro``   (space-separated, unquoted)
    - ``--model=gemini-3.1-pro``   (equals-separated, unquoted)
    - ``--model "Gemini 3.5 Flash"`` / ``--model='Gemini 3.5 Flash'`` (quoted,
      with spaces; either separator, either quote style)

    Returns the value with surrounding quotes stripped.
    """
    match = re.search(
        r"--model(?:\s+|=)(?:\"([^\"]+)\"|'([^']+)'|(\S+))",
        command,
    )
    if not match:
        return None
    return match.group(1) or match.group(2) or match.group(3)


# Command-position anchor: start of string, or after a shell separator
# (``|``, ``&``, ``;``, newline), optionally preceded by ``VAR=val`` env
# assignments. Used to classify the invoked binary while ignoring the same
# tokens if they only appear inside a quoted prompt body.
_CMD_START = r"(?:^|[|&;\n]\s*)(?:\w+=\S+\s+)*"


def detect_tool(command: str) -> str | None:
    """Return ``"codex"`` or ``"agy"`` based on the invoked binary.

    We must not classify by substring on the whole command: an agy call such
    as ``agy -p "analyze this codex error @err.png"`` legitimately contains
    the word "codex" inside its prompt body. Anchoring on command-start
    positions ensures we look at the executable, not the prompt.

    If both binaries appear at command-start (e.g. shell pipeline), the one
    executed first wins.
    """
    codex_match = re.search(_CMD_START + r"codex\b", command)
    agy_match = re.search(_CMD_START + r"agy\b", command)
    if codex_match and agy_match:
        return "codex" if codex_match.start() <= agy_match.start() else "agy"
    if codex_match:
        return "codex"
    if agy_match:
        return "agy"
    return None


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def recover_agy_output(prompt: str) -> str | None:
    """Best-effort recovery of agy output written only to brain artifacts.

    In non-TTY runs agy may exit 0 with empty stdout while the full result
    is saved under ``brain/<uuid>/`` (google-antigravity/antigravity-cli#408).
    ``brain/`` is global and parallel agy calls may be writing to it at the
    same time, so "newest run dir" alone is not enough: a run is only used
    if its ``transcript.jsonl`` contains this call's prompt, which ties the
    artifacts to the call being logged. Returns the concatenated ``*.md``
    artifacts of the matched run, or None when no run can be attributed.
    """
    brain_dir = _resolve_brain_dir()
    if not brain_dir.is_dir():
        return None
    needle = _normalize_whitespace(prompt)
    if not needle:
        return None
    try:
        run_dirs = sorted(
            (d for d in brain_dir.iterdir() if d.is_dir()),
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return None
    for run_dir in run_dirs[:MAX_BRAIN_RUNS_SCANNED]:
        transcript = run_dir / "transcript.jsonl"
        if not transcript.is_file():
            continue
        try:
            transcript_text = transcript.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle not in _normalize_whitespace(transcript_text):
            # Belongs to a different (possibly parallel) agy run.
            continue
        parts = []
        for artifact in sorted(run_dir.glob("*.md")):
            try:
                content = artifact.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if content.strip():
                parts.append(content.strip())
        return "\n\n".join(parts) or None
    return None


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
    """Log a Codex/agy call if the command matches; return notification dict or None."""
    tool_input = data.get("tool_input", {})
    tool_response = data.get("tool_response", {})

    command = tool_input.get("command", "")
    output = tool_response.get("stdout", "") or tool_response.get("content", "")

    tool = detect_tool(command)
    if tool is None:
        return None

    if tool == "codex":
        prompt = extract_codex_prompt(command)
        model = extract_model(command) or "default"
    else:
        prompt = extract_agy_prompt(command)
        # agy supports multiple models via `--model`; record the flag value
        # when present and fall back to the tool name for the default case.
        model = extract_model(command) or "agy"

    if not prompt:
        return None

    exit_code = tool_response.get("exit_code", 0)

    # Non-TTY agy runs may exit 0 with empty stdout while the result went to
    # brain artifacts only; recover it so the consultation is not recorded as
    # a failed/empty one (see recover_agy_output).
    recovered_from_brain = False
    stdout_empty = False
    if tool == "agy" and exit_code == 0 and not output:
        brain_output = recover_agy_output(prompt)
        if brain_output:
            output = brain_output
            recovered_from_brain = True
        else:
            stdout_empty = True

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
    if recovered_from_brain:
        entry["recovered_from_brain"] = True
    if stdout_empty:
        # exit 0 + no output + no attributable brain run: outcome unknown,
        # not a confirmed failure — let downstream consumers tell them apart.
        entry["stdout_empty"] = True

    _log_entry(entry)

    return {
        "additionalContext": f"[LOG] {tool.capitalize()} call logged to .claude/logs/cli-tools.jsonl",
    }
