"""Unit tests for the Multimodal section filter in checkpoint.generate_checkpoint.

The checkpoint script buckets CLI entries into ``codex`` and ``agy`` sections.
Pre-migration history uses ``tool: "gemini"`` and must still surface in the
Multimodal section after the agy migration.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_checkpoint_module():
    """Load the checkpoint script as a module without executing ``main``."""
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / ".claude" / "skills" / "checkpointing" / "checkpoint.py"
    spec = importlib.util.spec_from_file_location("checkpoint_under_test", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["checkpoint_under_test"] = module
    spec.loader.exec_module(module)
    return module


def _make_entry(tool: str, prompt: str) -> dict:
    return {
        "timestamp": "2026-07-15T00:00:00+00:00",
        "tool": tool,
        "model": tool,
        "prompt": prompt,
        "response": "ok",
        "success": True,
        "exit_code": 0,
    }


def _empty_file_changes() -> dict[str, list[str]]:
    return {"created": [], "modified": [], "deleted": []}


def test_gemini_entries_surface_in_multimodal_section():
    """Pre-migration ``tool: "gemini"`` entries must appear under Multimodal (agy)."""
    checkpoint = _load_checkpoint_module()
    cli_entries = [
        _make_entry("gemini", "extract API spec from @doc.pdf"),
        _make_entry("codex", "review the plan"),
    ]

    content = checkpoint.generate_checkpoint(
        commits=[],
        file_changes=_empty_file_changes(),
        file_stats={},
        cli_entries=cli_entries,
        teams_data=[],
        work_logs={},
        design_diff=None,
        branch="feat/agy-migration",
        since=None,
    )

    assert "## CLI Consultations" in content
    assert "Multimodal (agy)" in content
    assert "extract API spec from @doc.pdf" in content
    # Summary line should count gemini as a multimodal task.
    assert "**Multimodal (agy)**: 1" in content
    # And "No CLI consultations recorded." must NOT appear.
    assert "No CLI consultations recorded." not in content


def test_only_gemini_entries_still_render_multimodal_section():
    """Even with zero codex entries, gemini-only history keeps the section populated."""
    checkpoint = _load_checkpoint_module()
    cli_entries = [_make_entry("gemini", "transcribe @audio.mp3")]

    content = checkpoint.generate_checkpoint(
        commits=[],
        file_changes=_empty_file_changes(),
        file_stats={},
        cli_entries=cli_entries,
        teams_data=[],
        work_logs={},
        design_diff=None,
        branch="feat/agy-migration",
        since=None,
    )

    assert "Multimodal (agy)" in content
    assert "transcribe @audio.mp3" in content
    assert "No CLI consultations recorded." not in content
