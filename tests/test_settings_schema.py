"""Validate .claude/settings.json hook references and structure."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SETTINGS_REL_PATH = Path(".claude") / "settings.json"
HOOK_PATH_PATTERN = re.compile(
    r"\$CLAUDE_PROJECT_DIR/\.claude/hooks/(?P<name>[\w./-]+\.py)"
)
ECHO_INLINE_PATTERN = re.compile(r"^echo\s+'(.+)'\s*$", re.DOTALL)

EXPECTED_EVENTS = {
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "TeammateIdle",
    "TaskCompleted",
    "PreCompact",
}


@pytest.fixture(scope="module")
def settings(project_root: Path) -> dict:
    settings_path = project_root / SETTINGS_REL_PATH
    with open(settings_path, encoding="utf-8") as f:
        return json.load(f)


def test_settings_json_is_valid_object(settings: dict):
    assert isinstance(settings, dict), "settings.json root must be an object"
    assert "hooks" in settings, "settings.json must declare a 'hooks' key"


def test_all_known_event_names_present(settings: dict):
    declared_events = set(settings["hooks"].keys())
    missing = EXPECTED_EVENTS - declared_events
    assert not missing, f"Missing expected hook events: {missing}"


def _iter_hook_commands(hooks_section: dict):
    for event_name, matchers in hooks_section.items():
        for matcher_block in matchers:
            for hook_entry in matcher_block.get("hooks", []):
                yield event_name, hook_entry


def test_every_hook_entry_has_required_fields(settings: dict):
    for event, entry in _iter_hook_commands(settings["hooks"]):
        assert entry.get("type") == "command", (
            f"{event}: hook entry must have type='command' (got {entry.get('type')!r})"
        )
        assert "command" in entry and entry["command"], (
            f"{event}: hook entry missing non-empty command"
        )


def test_hook_timeouts_are_positive_ints_when_present(settings: dict):
    for event, entry in _iter_hook_commands(settings["hooks"]):
        if "timeout" not in entry:
            continue
        timeout = entry["timeout"]
        assert isinstance(timeout, int), (
            f"{event}: timeout must be int, got {type(timeout)}"
        )
        assert timeout > 0, f"{event}: timeout must be positive, got {timeout}"


def test_referenced_hook_scripts_exist(project_root: Path, settings: dict):
    hooks_root = project_root / ".claude" / "hooks"
    missing: list[tuple[str, str]] = []
    for event, entry in _iter_hook_commands(settings["hooks"]):
        cmd = entry["command"]
        for match in HOOK_PATH_PATTERN.finditer(cmd):
            hook_file = hooks_root / match.group("name")
            if not hook_file.exists():
                missing.append((event, str(hook_file)))
    assert not missing, f"Referenced hook scripts do not exist: {missing}"


def test_no_references_to_deleted_hook_scripts(settings: dict):
    """PR #2 deleted error-to-codex.py and post-test-analysis.py."""
    deleted_scripts = {"error-to-codex.py", "post-test-analysis.py"}
    for event, entry in _iter_hook_commands(settings["hooks"]):
        cmd = entry["command"]
        for deleted in deleted_scripts:
            assert deleted not in cmd, (
                f"{event}: command still references deleted script {deleted!r}: {cmd}"
            )


def test_inline_echo_commands_emit_valid_json(settings: dict):
    for event, entry in _iter_hook_commands(settings["hooks"]):
        cmd = entry["command"].strip()
        match = ECHO_INLINE_PATTERN.match(cmd)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"{event}: inline echo command emits invalid JSON: {exc}\n{cmd}"
            )
        assert isinstance(parsed, dict), f"{event}: inline echo must emit a JSON object"


def test_post_tool_use_bash_dispatcher_is_single_entry(settings: dict):
    """PR #2 consolidated 3 PostToolUse:Bash hooks into 1 dispatcher."""
    bash_blocks = [
        block
        for block in settings["hooks"].get("PostToolUse", [])
        if block.get("matcher") == "Bash"
    ]
    assert bash_blocks, "PostToolUse must declare a Bash matcher"
    total_bash_hooks = sum(len(block.get("hooks", [])) for block in bash_blocks)
    assert total_bash_hooks == 1, (
        f"PostToolUse:Bash should run a single dispatcher, got {total_bash_hooks} hooks"
    )
    cmd = bash_blocks[0]["hooks"][0]["command"]
    assert "bash-postdispatch.py" in cmd, f"Expected dispatcher in command, got: {cmd}"
