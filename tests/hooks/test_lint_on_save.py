"""Unit tests for .claude/hooks/lint-on-save.py.

Strategy: prepend a tmp dir containing a stub `uv` to PATH so the hook invokes
our fake instead of the real ruff/ty toolchain. The stub records each
invocation to a JSONL file so tests can assert on argument order and counts.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest


HOOK = "lint-on-save.py"


def _write_uv_stub(bin_dir: Path, log_file: Path, exit_code: int = 0) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys, os\n"
        f"log_path = {str(log_file)!r}\n"
        "with open(log_path, 'a', encoding='utf-8') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        f"sys.exit({exit_code})\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _payload(file_path: str) -> dict:
    return {"tool_input": {"file_path": file_path}}


def test_python_file_invokes_ruff_then_ty_in_order(hook_runner, tmp_path: Path):
    bin_dir = tmp_path / "stub-bin"
    log_file = tmp_path / "calls.jsonl"
    _write_uv_stub(bin_dir, log_file, exit_code=0)

    py_file = tmp_path / "sample.py"
    py_file.write_text("x = 1\n")

    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = hook_runner(HOOK, _payload(str(py_file)), env=env)

    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "OK" in result.stdout

    calls = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert len(calls) == 3, f"Expected 3 uv calls (ruff check, ruff format, ty check); got: {calls}"
    # Order matters: ruff check --fix → ruff format → ty check
    assert calls[0][:4] == ["run", "ruff", "check", "--fix"]
    assert calls[1][:3] == ["run", "ruff", "format"]
    assert calls[2][:3] == ["run", "ty", "check"]
    # All three should target the same file (last positional arg).
    for call in calls:
        assert call[-1] == str(py_file)


def test_non_python_file_skipped(hook_runner, tmp_path: Path):
    bin_dir = tmp_path / "stub-bin"
    log_file = tmp_path / "calls.jsonl"
    _write_uv_stub(bin_dir, log_file)

    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello")

    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = hook_runner(HOOK, _payload(str(txt_file)), env=env)

    assert result.returncode == 0
    assert not log_file.exists(), "uv must not be invoked for non-Python files"


def test_path_traversal_rejected(hook_runner, tmp_path: Path):
    bin_dir = tmp_path / "stub-bin"
    log_file = tmp_path / "calls.jsonl"
    _write_uv_stub(bin_dir, log_file)

    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = hook_runner(HOOK, _payload("../etc/passwd.py"), env=env)

    assert result.returncode == 0
    assert not log_file.exists(), "uv must not be invoked for paths containing '..'"


def test_missing_file_path_skipped(hook_runner, tmp_path: Path):
    bin_dir = tmp_path / "stub-bin"
    log_file = tmp_path / "calls.jsonl"
    _write_uv_stub(bin_dir, log_file)

    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = hook_runner(HOOK, {"tool_input": {}}, env=env)

    assert result.returncode == 0
    assert not log_file.exists()


def test_ruff_failure_surfaces_to_stderr(hook_runner, tmp_path: Path):
    """If uv exits non-zero with stdout content, the hook reports it on stderr."""
    bin_dir = tmp_path / "stub-bin"
    log_file = tmp_path / "calls.jsonl"
    # Stub that exits 1 with a fake lint complaint on stdout.
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('E501 line too long')\n"
        "sys.exit(1)\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    py_file = tmp_path / "sample.py"
    py_file.write_text("x = 1\n")

    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = hook_runner(HOOK, _payload(str(py_file)), env=env)

    assert result.returncode == 0  # Hook itself never blocks
    assert "Issues found" in result.stderr
    assert "E501" in result.stderr
