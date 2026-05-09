"""Unit tests for .claude/hooks/suggest-gemini-research.py (PreToolUse:WebSearch|WebFetch)."""

from __future__ import annotations

import json


HOOK = "suggest-gemini-research.py"


def _parse(stdout: str) -> dict | None:
    stdout = stdout.strip()
    return json.loads(stdout) if stdout else None


def test_web_search_documentation_query_triggers_suggestion(hook_runner):
    payload = {
        "tool_name": "WebSearch",
        "tool_input": {"query": "anthropic claude api documentation"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
    assert "Research Suggestion" in out["hookSpecificOutput"]["additionalContext"]


def test_simple_lookup_skipped(hook_runner):
    payload = {
        "tool_name": "WebSearch",
        "tool_input": {"query": "stack trace something"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_long_query_triggers_suggestion(hook_runner):
    payload = {
        "tool_name": "WebSearch",
        "tool_input": {"query": "x" * 150},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None


def test_web_fetch_routing(hook_runner):
    payload = {
        "tool_name": "WebFetch",
        "tool_input": {"url": "https://docs.example.com/library/api", "prompt": "find best practice"},
    }
    result = hook_runner(HOOK, payload)
    assert result.returncode == 0
    out = _parse(result.stdout)
    assert out is not None
