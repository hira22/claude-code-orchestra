#!/usr/bin/env python3
"""PostToolUse:Bash dispatcher.

Replaces three separate hook commands (error-to-codex, post-test-analysis,
log-cli-tools) with a single python3 entry point. Each handler runs inside
its own try/except so a failure in one does not silence the others.
"""

import json
import sys
from pathlib import Path

# Ensure `lib/` (sibling package) is importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import cli_logger, error_detector, test_analyzer  # noqa: E402

HANDLERS = [
    ("error-detector", error_detector.check),
    ("test-analyzer", test_analyzer.check),
    ("cli-logger", cli_logger.check),
]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    contexts: list[str] = []
    event_name = "PostToolUse"

    for name, handler in HANDLERS:
        try:
            result = handler(data)
        except Exception as exc:
            print(f"[{name}] Hook error: {exc}", file=sys.stderr)
            continue
        if not result:
            continue
        ctx = result.get("additionalContext")
        if ctx:
            contexts.append(ctx)
        if "hookEventName" in result:
            event_name = result["hookEventName"]

    if not contexts:
        sys.exit(0)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event_name,
                    "additionalContext": "\n".join(contexts),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
