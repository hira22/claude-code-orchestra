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
