#!/usr/bin/env bash
# Unit tests for the merge_settings_json function in bin/orchestra-init.
#
# Run with: bash tests/test_merge_hooks.sh
# Exits 0 if every assertion passes, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORCHESTRA_INIT="$SCRIPT_DIR/../bin/orchestra-init"

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required to run these tests" >&2
    exit 2
fi

# Source for merge_settings_json. The script's source guard skips its CLI flow.
# shellcheck source=../bin/orchestra-init
source "$ORCHESTRA_INIT"

PASS=0
FAIL=0
FAILED_NAMES=()

run_case() {
    local name="$1"
    local existing_json="$2"
    local template_json="$3"
    local expected_hooks_json="$4"

    local existing template actual
    existing="$(mktemp)"
    template="$(mktemp)"
    actual="$(mktemp)"
    printf '%s' "$existing_json" > "$existing"
    printf '%s' "$template_json" > "$template"

    merge_settings_json "$existing" "$template" "$actual"

    local actual_hooks expected_hooks
    actual_hooks=$(jq -S '.hooks' "$actual")
    expected_hooks=$(printf '%s' "$expected_hooks_json" | jq -S '.')

    if [ "$actual_hooks" = "$expected_hooks" ]; then
        PASS=$((PASS + 1))
        printf '✓ %s\n' "$name"
    else
        FAIL=$((FAIL + 1))
        FAILED_NAMES+=("$name")
        printf '✗ %s\n' "$name"
        echo "  --- expected ---"
        printf '%s\n' "$expected_hooks" | sed 's/^/  /'
        echo "  --- actual ---"
        printf '%s\n' "$actual_hooks" | sed 's/^/  /'
    fi

    rm -f "$existing" "$template" "$actual"
}

# ─────────────────────────────────────────────────────────────────────────────
# T1: PR#2 scenario — existing has 3 same-matcher entries, template has 1.
# Expected: 1 entry with 4 commands (template-first union).
# ─────────────────────────────────────────────────────────────────────────────
run_case "T1 union same-matcher entries (PR#2 scenario)" \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "old1.py", "timeout": 30 }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "old2.py", "timeout": 30 }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "old3.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "dispatcher.py", "timeout": 10 }] }
    ]
  }
}' \
'{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [
      { "type": "command", "command": "dispatcher.py", "timeout": 10 },
      { "type": "command", "command": "old1.py", "timeout": 30 },
      { "type": "command", "command": "old2.py", "timeout": 30 },
      { "type": "command", "command": "old3.py", "timeout": 5 }
    ] }
  ]
}'

# ─────────────────────────────────────────────────────────────────────────────
# T2: same command on both sides with different timeouts → template wins.
# ─────────────────────────────────────────────────────────────────────────────
run_case "T2 template timeout wins on same command" \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "lint.py", "timeout": 30 }] }
    ]
  }
}' \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "lint.py", "timeout": 100 }] }
    ]
  }
}' \
'{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [{ "type": "command", "command": "lint.py", "timeout": 100 }] }
  ]
}'

# ─────────────────────────────────────────────────────────────────────────────
# T3: idempotent — merging identical inputs produces the same hooks shape.
# ─────────────────────────────────────────────────────────────────────────────
IDENTICAL='{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit", "hooks": [{ "type": "command", "command": "guard.py", "timeout": 5 }] }
    ]
  }
}'
IDENTICAL_HOOKS='{
  "PreToolUse": [
    { "matcher": "Edit", "hooks": [{ "type": "command", "command": "guard.py", "timeout": 5 }] }
  ]
}'
run_case "T3 idempotent merge" "$IDENTICAL" "$IDENTICAL" "$IDENTICAL_HOOKS"

# ─────────────────────────────────────────────────────────────────────────────
# T4: user added a custom command under a shared matcher → both kept.
# ─────────────────────────────────────────────────────────────────────────────
run_case "T4 user custom command under shared matcher preserved" \
'{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit", "hooks": [
        { "type": "command", "command": "guard.py", "timeout": 5 },
        { "type": "command", "command": "user-custom.py", "timeout": 5 }
      ] }
    ]
  }
}' \
'{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Edit", "hooks": [{ "type": "command", "command": "guard.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "PreToolUse": [
    { "matcher": "Edit", "hooks": [
      { "type": "command", "command": "guard.py", "timeout": 5 },
      { "type": "command", "command": "user-custom.py", "timeout": 5 }
    ] }
  ]
}'

# ─────────────────────────────────────────────────────────────────────────────
# T5: user has a custom matcher that template never declares → preserved.
# ─────────────────────────────────────────────────────────────────────────────
run_case "T5 user-only matcher preserved verbatim" \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "shared.py", "timeout": 5 }] },
      { "matcher": "Edit", "hooks": [{ "type": "command", "command": "user-only.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "shared.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [{ "type": "command", "command": "shared.py", "timeout": 5 }] },
    { "matcher": "Edit", "hooks": [{ "type": "command", "command": "user-only.py", "timeout": 5 }] }
  ]
}'

# ─────────────────────────────────────────────────────────────────────────────
# T6: matcher ordering follows first-seen, NOT alphabetical.
# Template emits Task before Bash; merged output must keep that order.
# ─────────────────────────────────────────────────────────────────────────────
run_case "T6 first-seen matcher order preserved (no alpha sort)" \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "old.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Task", "hooks": [{ "type": "command", "command": "task.py", "timeout": 5 }] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "new.py", "timeout": 5 }] }
    ]
  }
}' \
'{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [
      { "type": "command", "command": "new.py", "timeout": 5 },
      { "type": "command", "command": "old.py", "timeout": 5 }
    ] },
    { "matcher": "Task", "hooks": [{ "type": "command", "command": "task.py", "timeout": 5 }] }
  ]
}'

# ─────────────────────────────────────────────────────────────────────────────
# T7: hook execution order preserved when deduping multi-command hooks.
# The old `unique_by(.command)` would alpha-sort the array on every merge,
# silently reordering hook execution. The new insertion-order reduce must
# return the input list unchanged for an idempotent self-merge.
# Commands deliberately listed in non-alphabetical order to expose the bug.
# ─────────────────────────────────────────────────────────────────────────────
ORDER_INPUT='{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "zebra.py", "timeout": 5 },
        { "type": "command", "command": "alpha.py", "timeout": 5 },
        { "type": "command", "command": "mango.py", "timeout": 5 }
      ] }
    ]
  }
}'
ORDER_EXPECTED='{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [
      { "type": "command", "command": "zebra.py", "timeout": 5 },
      { "type": "command", "command": "alpha.py", "timeout": 5 },
      { "type": "command", "command": "mango.py", "timeout": 5 }
    ] }
  ]
}'
run_case "T7 hook order preserved on idempotent multi-command merge" \
    "$ORDER_INPUT" "$ORDER_INPUT" "$ORDER_EXPECTED"

# ─────────────────────────────────────────────────────────────────────────────
# T8: prune_settings_hooks_for_paths matches on path boundaries.
# Deleting `.claude/hooks/foo.py` must NOT prune a still-present command
# referencing `.claude/hooks/foo-old/run.py` (substring overlap).
# ─────────────────────────────────────────────────────────────────────────────
T8_INPUT="$(mktemp)"
T8_ACTUAL="$(mktemp)"
cat > "$T8_INPUT" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/foo.py\"", "timeout": 5 },
        { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/foo-old/run.py\"", "timeout": 5 }
      ] }
    ]
  }
}
JSON
prune_settings_hooks_for_paths "$T8_INPUT" '[".claude/hooks/foo.py"]' "$T8_ACTUAL"
T8_EXPECTED='{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [
      { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/foo-old/run.py\"", "timeout": 5 }
    ] }
  ]
}'
T8_ACTUAL_HOOKS=$(jq -S '.hooks' "$T8_ACTUAL")
T8_EXPECTED_HOOKS=$(printf '%s' "$T8_EXPECTED" | jq -S '.')
if [ "$T8_ACTUAL_HOOKS" = "$T8_EXPECTED_HOOKS" ]; then
    PASS=$((PASS + 1))
    echo "✓ T8 prune respects path boundary (foo vs foo-old)"
else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T8 prune respects path boundary (foo vs foo-old)")
    echo "✗ T8 prune respects path boundary (foo vs foo-old)"
    echo "  --- expected ---"
    printf '%s\n' "$T8_EXPECTED_HOOKS" | sed 's/^/  /'
    echo "  --- actual ---"
    printf '%s\n' "$T8_ACTUAL_HOOKS" | sed 's/^/  /'
fi
rm -f "$T8_INPUT" "$T8_ACTUAL"

# ─────────────────────────────────────────────────────────────────────────────
# T9: prune with directory-prefix path (Case A: __ALL__ → ".claude/hooks/").
# Every command containing the directory prefix should be pruned.
# ─────────────────────────────────────────────────────────────────────────────
T9_INPUT="$(mktemp)"
T9_ACTUAL="$(mktemp)"
cat > "$T9_INPUT" <<'JSON'
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/a.py\"", "timeout": 5 },
        { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/lib/b.py\"", "timeout": 5 }
      ] },
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "echo unrelated", "timeout": 5 }] }
    ]
  }
}
JSON
prune_settings_hooks_for_paths "$T9_INPUT" '[".claude/hooks/"]' "$T9_ACTUAL"
T9_EXPECTED='{
  "PostToolUse": [
    { "matcher": "Bash", "hooks": [{ "type": "command", "command": "echo unrelated", "timeout": 5 }] }
  ]
}'
T9_ACTUAL_HOOKS=$(jq -S '.hooks' "$T9_ACTUAL")
T9_EXPECTED_HOOKS=$(printf '%s' "$T9_EXPECTED" | jq -S '.')
if [ "$T9_ACTUAL_HOOKS" = "$T9_EXPECTED_HOOKS" ]; then
    PASS=$((PASS + 1))
    echo "✓ T9 prune with directory-prefix path removes all descendants"
else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T9 prune directory-prefix")
    echo "✗ T9 prune with directory-prefix path removes all descendants"
    echo "  --- expected ---"
    printf '%s\n' "$T9_EXPECTED_HOOKS" | sed 's/^/  /'
    echo "  --- actual ---"
    printf '%s\n' "$T9_ACTUAL_HOOKS" | sed 's/^/  /'
fi
rm -f "$T9_INPUT" "$T9_ACTUAL"

# ─────────────────────────────────────────────────────────────────────────────
# T10: merge_settings_json prunes deprecated env keys from the existing side.
# PR#6 removed CLAUDE_CODE_SUBAGENT_MODEL. Existing installs must lose that
# key on update while unrelated user-added env vars are preserved.
# ─────────────────────────────────────────────────────────────────────────────
T10_EXISTING="$(mktemp)"
T10_TEMPLATE="$(mktemp)"
T10_ACTUAL="$(mktemp)"
cat > "$T10_EXISTING" <<'JSON'
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "claude-opus-4-6",
    "EDITOR": "vim",
    "USER_CUSTOM_VAR": "keep-me"
  }
}
JSON
cat > "$T10_TEMPLATE" <<'JSON'
{
  "env": {
    "EDITOR": "code --wait",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
JSON
merge_settings_json "$T10_EXISTING" "$T10_TEMPLATE" "$T10_ACTUAL" '["CLAUDE_CODE_SUBAGENT_MODEL"]'
T10_ACTUAL_ENV=$(jq -S '.env' "$T10_ACTUAL")
# Expected:
#  - CLAUDE_CODE_SUBAGENT_MODEL removed (deprecated tombstone)
#  - USER_CUSTOM_VAR preserved (user-added, not deprecated)
#  - EDITOR overridden by template value ("template wins on conflict")
#  - CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS carried in from template
T10_EXPECTED_ENV=$(cat <<'JSON' | jq -S '.'
{
  "EDITOR": "code --wait",
  "USER_CUSTOM_VAR": "keep-me",
  "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
}
JSON
)
if [ "$T10_ACTUAL_ENV" = "$T10_EXPECTED_ENV" ]; then
    PASS=$((PASS + 1))
    echo "✓ T10 deprecated env key pruned, user-added key preserved"
else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T10 deprecated env prune")
    echo "✗ T10 deprecated env key pruned, user-added key preserved"
    echo "  --- expected ---"
    printf '%s\n' "$T10_EXPECTED_ENV" | sed 's/^/  /'
    echo "  --- actual ---"
    printf '%s\n' "$T10_ACTUAL_ENV" | sed 's/^/  /'
fi
rm -f "$T10_EXISTING" "$T10_TEMPLATE" "$T10_ACTUAL"

# ─────────────────────────────────────────────────────────────────────────────
# T11: default (no deprecated list passed) preserves legacy union behavior.
# Callers that omit the 4th arg — e.g. earlier tests in this file — must not
# be affected by the new pruning path.
# ─────────────────────────────────────────────────────────────────────────────
T11_EXISTING="$(mktemp)"
T11_TEMPLATE="$(mktemp)"
T11_ACTUAL="$(mktemp)"
cat > "$T11_EXISTING" <<'JSON'
{ "env": { "OLD_KEY": "still-here", "SHARED": "existing" } }
JSON
cat > "$T11_TEMPLATE" <<'JSON'
{ "env": { "SHARED": "template", "NEW_KEY": "added" } }
JSON
merge_settings_json "$T11_EXISTING" "$T11_TEMPLATE" "$T11_ACTUAL"
T11_ACTUAL_ENV=$(jq -S '.env' "$T11_ACTUAL")
T11_EXPECTED_ENV=$(cat <<'JSON' | jq -S '.'
{ "OLD_KEY": "still-here", "SHARED": "template", "NEW_KEY": "added" }
JSON
)
if [ "$T11_ACTUAL_ENV" = "$T11_EXPECTED_ENV" ]; then
    PASS=$((PASS + 1))
    echo "✓ T11 default deprecated list is empty (union preserved)"
else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T11 default deprecated list empty")
    echo "✗ T11 default deprecated list is empty (union preserved)"
    echo "  --- expected ---"
    printf '%s\n' "$T11_EXPECTED_ENV" | sed 's/^/  /'
    echo "  --- actual ---"
    printf '%s\n' "$T11_ACTUAL_ENV" | sed 's/^/  /'
fi
rm -f "$T11_EXISTING" "$T11_TEMPLATE" "$T11_ACTUAL"

# ─────────────────────────────────────────────────────────────────────────────
# T12: CLI-configured DEPRECATED_ENV_KEYS_JSON currently lists
# CLAUDE_CODE_SUBAGENT_MODEL. This anchors the "PR#6 fix" contract: any
# future edit that drops the key from the list will fail here and force
# reviewers to re-justify.
# ─────────────────────────────────────────────────────────────────────────────
if echo "$DEPRECATED_ENV_KEYS_JSON" | jq -e 'index("CLAUDE_CODE_SUBAGENT_MODEL") != null' >/dev/null; then
    PASS=$((PASS + 1))
    echo "✓ T12 DEPRECATED_ENV_KEYS_JSON contains CLAUDE_CODE_SUBAGENT_MODEL"
else
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T12 DEPRECATED_ENV_KEYS_JSON contract")
    echo "✗ T12 DEPRECATED_ENV_KEYS_JSON contains CLAUDE_CODE_SUBAGENT_MODEL"
    echo "  --- actual DEPRECATED_ENV_KEYS_JSON ---"
    printf '  %s\n' "$DEPRECATED_ENV_KEYS_JSON"
fi

# ─────────────────────────────────────────────────────────────────────────────
# T13: fresh-install parity — the shipped template `.claude/settings.json`
# must not itself contain the deprecated env key (otherwise a `cp -r` on a
# clean machine would immediately re-introduce it). Method (b) means the
# template only needs to be free of the retired key; there are no meta keys
# to strip. Guarding this in a test keeps future template edits honest.
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATE_SETTINGS="$SCRIPT_DIR/../.claude/settings.json"
if [ -f "$TEMPLATE_SETTINGS" ]; then
    if jq -e '.env.CLAUDE_CODE_SUBAGENT_MODEL' "$TEMPLATE_SETTINGS" >/dev/null 2>&1; then
        FAIL=$((FAIL + 1))
        FAILED_NAMES+=("T13 template contains deprecated env key")
        echo "✗ T13 template settings.json must not contain CLAUDE_CODE_SUBAGENT_MODEL"
    else
        PASS=$((PASS + 1))
        echo "✓ T13 template settings.json is free of deprecated env key"
    fi
else
    # Template file is a repo-level asset; missing it means the checkout is
    # broken. Fail loudly rather than silently skip.
    FAIL=$((FAIL + 1))
    FAILED_NAMES+=("T13 template settings.json missing")
    echo "✗ T13 template settings.json not found at $TEMPLATE_SETTINGS"
fi

echo
echo "=== Results: $PASS passed, $FAIL failed ==="
if [ "$FAIL" -ne 0 ]; then
    printf 'Failed:\n'
    for n in "${FAILED_NAMES[@]}"; do
        printf '  - %s\n' "$n"
    done
    exit 1
fi
exit 0
