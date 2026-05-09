"""Unit tests for .claude/hooks/check-codex-after-plan.py (PostToolUse:Task)."""

from __future__ import annotations

import json

HOOK = "check-codex-after-plan.py"


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    return json.loads(stdout) if stdout else None


def test_non_task_tool_skipped(hook_runner):
    result = hook_runner(HOOK, {"tool_name": "Bash", "tool_input": {"description": "design plan"}})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_plan_subagent_triggers_suggestion(hook_runner):
    payload = {
        "tool_name": "Task",
        "tool_input": {"subagent_type": "Plan", "description": "Plan migration"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
    assert "Codex Review Suggestion" in out["hookSpecificOutput"]["additionalContext"]


def test_plan_keyword_in_description_triggers_suggestion(hook_runner):
    payload = {
        "tool_name": "Task",
        "tool_input": {"subagent_type": "general-purpose", "description": "design new module"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None


def test_neutral_task_emits_nothing(hook_runner):
    payload = {
        "tool_name": "Task",
        "tool_input": {"subagent_type": "general-purpose", "description": "just say hi"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert result.stdout.strip() == ""
