"""Shared pytest fixtures for hook + skill + rule tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def hooks_dir(project_root: Path) -> Path:
    return project_root / ".claude" / "hooks"


@pytest.fixture(scope="session")
def skills_dir(project_root: Path) -> Path:
    return project_root / ".claude" / "skills"


@pytest.fixture(scope="session")
def rules_dir(project_root: Path) -> Path:
    return project_root / ".claude" / "rules"


HookRunner = Callable[..., subprocess.CompletedProcess]


@pytest.fixture
def hook_runner(project_root: Path, hooks_dir: Path) -> HookRunner:
    """Run a hook script with the given JSON payload via stdin.

    Sets CLAUDE_PROJECT_DIR to the project root so hooks resolve relative paths
    consistently. Extra environment variables can be passed via `env`.
    """

    def _run(
        hook_name: str,
        payload: dict[str, Any] | str,
        env: dict[str, str] | None = None,
        timeout: int = 10,
    ) -> subprocess.CompletedProcess:
        hook_path = hooks_dir / hook_name
        assert hook_path.exists(), f"Hook script not found: {hook_path}"
        full_env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project_root),
            **(env or {}),
        }
        stdin_str = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, str(hook_path)],
            input=stdin_str,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=full_env,
        )

    return _run


@pytest.fixture(scope="session")
def lib_module_path(hooks_dir: Path):
    """Insert .claude/hooks/ on sys.path so `from lib import ...` works in tests.

    Session-scoped because module-scoped fixtures depend on it.
    """
    hooks_str = str(hooks_dir)
    inserted = False
    if hooks_str not in sys.path:
        sys.path.insert(0, hooks_str)
        inserted = True
    try:
        yield hooks_dir
    finally:
        if inserted:
            sys.path.remove(hooks_str)
