#!/usr/bin/env python3
"""Post-tool hook: format + lint + type-check Python files after Edit/Write.

Runs ruff check --fix -> ruff format -> ty check sequentially. The ruff
sequence mutates the file (auto-fix and format both rewrite it), so ty
must observe the post-ruff state to avoid reporting stale type errors
against pre-fix code (e.g. unused-import that ruff just removed).
"""

import json
import os
import subprocess
import sys

MAX_PATH_LENGTH = 4096
SUBPROCESS_TIMEOUT = (
    30  # cold-start `uv run ruff/ty` can exceed 15s on first invocation
)


def validate_path(file_path: str) -> bool:
    if not file_path or len(file_path) > MAX_PATH_LENGTH:
        return False
    if ".." in file_path:
        return False
    return True


def get_file_path() -> str | None:
    try:
        data = json.load(sys.stdin)
        return data.get("tool_input", {}).get("file_path")
    except (json.JSONDecodeError, Exception):
        return None


def is_python_file(path: str) -> bool:
    return path.endswith(".py")


def _run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


def run_ruff_sequence(file_path: str, cwd: str) -> list[str]:
    """ruff check --fix -> ruff format. Both mutate the file, so sequential."""
    issues: list[str] = []

    ret, stdout, stderr = _run(["uv", "run", "ruff", "check", "--fix", file_path], cwd)
    if ret != 0:
        output = stdout or stderr
        if output.strip():
            issues.append(f"ruff check issues:\n{output}")

    ret, stdout, stderr = _run(["uv", "run", "ruff", "format", file_path], cwd)
    if ret != 0:
        output = stderr or stdout
        if output.strip():
            issues.append(f"ruff format failed:\n{output}")

    return issues


def run_ty_check(file_path: str, cwd: str) -> list[str]:
    """ty check; must run AFTER the ruff sequence so it sees the post-fix state."""
    ret, stdout, stderr = _run(["uv", "run", "ty", "check", file_path], cwd)
    if ret == 0:
        return []
    output = stdout or stderr
    return [f"ty check issues:\n{output}"] if output.strip() else []


def main() -> None:
    file_path = get_file_path()
    if not file_path or not validate_path(file_path) or not is_python_file(file_path):
        return

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    rel_path = (
        os.path.relpath(file_path, project_dir)
        if file_path.startswith(project_dir)
        else file_path
    )

    # ty must observe the post-ruff state, so the order is strict:
    # ruff check --fix -> ruff format (both rewrite the file) -> ty check.
    issues = run_ruff_sequence(file_path, project_dir)
    issues += run_ty_check(file_path, project_dir)

    if issues:
        print(f"[lint-on-save] Issues found in {rel_path}:", file=sys.stderr)
        for issue in issues:
            print(issue, file=sys.stderr)
        print("\nPlease review and fix these issues.", file=sys.stderr)
    else:
        print(f"[lint-on-save] OK: {rel_path} passed all checks")


if __name__ == "__main__":
    main()
