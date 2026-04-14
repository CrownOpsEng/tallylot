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


def changed_repo_paths() -> tuple[str, ...]:
    tracked = _git_paths("diff", "--name-only", "--diff-filter=ACMR", "HEAD")
    untracked = _git_paths("ls-files", "--others", "--exclude-standard")
    seen: dict[str, None] = {}
    for path in (*tracked, *untracked):
        seen[path] = None
    return tuple(seen)


def _paths_with_suffixes(paths: Iterable[str], suffixes: set[str]) -> tuple[str, ...]:
    return tuple(path for path in paths if Path(path).suffix in suffixes)


def _run_command(command: tuple[str, ...], *, env: dict[str, str] | None = None) -> int:
    print(f"[auto-fix] {' '.join(command)}", flush=True)
    return subprocess.run(command, check=False, env=env).returncode


def run_local_autofix() -> int:
    changed_paths = changed_repo_paths()
    if not changed_paths:
        print("[auto-fix] no changed paths detected", flush=True)
        return 0

    python_paths = _paths_with_suffixes(changed_paths, PYTHON_SUFFIXES)
    markdown_paths = _paths_with_suffixes(changed_paths, MARKDOWN_SUFFIXES)

    if python_paths:
        python_env = repo_uv_environment()
        for command in (
            ("uv", "run", "ruff", "check", "--fix", *python_paths),
            ("uv", "run", "ruff", "format", *python_paths),
        ):
            status = _run_command(command, env=python_env)
            if status != 0:
                return status

    if markdown_paths and shutil.which("markdownlint") is not None:
        markdown_env = os.environ.copy()
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
