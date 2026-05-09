"""Unit tests for .claude/hooks/agent-router.py (UserPromptSubmit)."""

from __future__ import annotations

import json


HOOK = "agent-router.py"


def _parse_output(stdout: str) -> dict | None:
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def test_short_prompt_emits_nothing(hook_runner):
    result = hook_runner(HOOK, {"prompt": "hi"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_multimodal_pdf_routes_to_gemini(hook_runner):
    result = hook_runner(HOOK, {"prompt": "Please summarize report.pdf for me"})
    assert result.returncode == 0
    out = _parse_output(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Multimodal File Detected" in ctx
    assert "report.pdf" in ctx


def test_multimodal_japanese_adjacent_extension_strips_prefix(hook_runner):
    """Regression: `このreport.pdfを読んで` should yield path `report.pdf`, not `このreport.pdf`."""
    result = hook_runner(HOOK, {"prompt": "このreport.pdfを読んで"})
    assert result.returncode == 0
    out = _parse_output(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "@report.pdf" in ctx
    assert "@このreport.pdf" not in ctx


def test_codex_routing_on_design_keyword(hook_runner):
    result = hook_runner(HOOK, {"prompt": "アーキテクチャを設計してください"})
    assert result.returncode == 0
    out = _parse_output(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Codex CLI" in ctx or "Agent Routing" in ctx


def test_codex_plugin_routing_takes_priority_over_codex(hook_runner):
    """`レビューして` is in CODEX_PLUGIN_TRIGGERS and should win over `レビュー` in CODEX_TRIGGERS."""
    result = hook_runner(HOOK, {"prompt": "このコードをレビューしてください"})
    assert result.returncode == 0
    out = _parse_output(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Codex Plugin" in ctx


def test_opus_research_routing_on_codebase_keyword(hook_runner):
    result = hook_runner(HOOK, {"prompt": "このコードベースを調べて全体構造を教えて"})
    assert result.returncode == 0
    out = _parse_output(result.stdout)
    assert out is not None
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Opus Research" in ctx


def test_no_routing_for_neutral_prompt(hook_runner):
    result = hook_runner(HOOK, {"prompt": "Hello there friend, how are you today?"})
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_invalid_json_does_not_crash(hook_runner):
    result = hook_runner(HOOK, "this is not json")
    assert result.returncode == 0
    assert "Hook error" in result.stderr or result.stderr == ""
