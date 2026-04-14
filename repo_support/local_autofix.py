from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from tools.uv_environment import repo_uv_environment

PYTHON_SUFFIXES = {".py", ".pyi"}
MARKDOWN_SUFFIXES = {".md", ".mdx"}


def _git_paths(*args: str) -> tuple[str, ...]:
    result = subprocess.run(
        ("git", *args),
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def staged_repo_paths() -> tuple[str, ...]:
    return _git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR")


def _paths_with_suffixes(paths: Iterable[str], suffixes: set[str]) -> tuple[str, ...]:
    return tuple(path for path in paths if Path(path).suffix in suffixes)


def _run_command(command: tuple[str, ...], *, env: dict[str, str] | None = None) -> int:
    print(f"[auto-fix] {' '.join(command)}", flush=True)
    return subprocess.run(command, check=False, env=env).returncode


def _markdownlint_available() -> bool:
    return shutil.which("markdownlint") is not None


def _markdownlint_environment() -> dict[str, str]:
    return os.environ.copy()


def run_local_autofix() -> int:
    staged_paths = staged_repo_paths()
    if not staged_paths:
        print("[auto-fix] no staged paths detected", flush=True)
        return 0

    python_paths = _paths_with_suffixes(staged_paths, PYTHON_SUFFIXES)
    markdown_paths = _paths_with_suffixes(staged_paths, MARKDOWN_SUFFIXES)

    if python_paths:
        python_env = repo_uv_environment()
        for command in (
            ("uv", "run", "ruff", "check", "--fix", *python_paths),
            ("uv", "run", "ruff", "format", *python_paths),
        ):
            status = _run_command(command, env=python_env)
            if status != 0:
                return status

    if markdown_paths and _markdownlint_available():
        markdown_env = _markdownlint_environment()
        status = _run_command(
            (
                "markdownlint",
                "--fix",
                "--config",
                ".markdownlint.json",
                *markdown_paths,
            ),
            env=markdown_env,
        )
        if status != 0:
            return status
    elif markdown_paths:
        print(
            "[auto-fix] markdownlint executable not available; skipping markdown autofix",
            flush=True,
        )

    return 0
