from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

PYTHON_SUFFIXES = {".py", ".pyi"}
_COMMIT_MSG_HOOK_NEEDLES = (
    "--hook-type=commit-msg",
    "pre_commit",
)


def _git_paths(*args: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return tuple(lines)


def _git_path(path: str) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--git-path", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def _hook_dir_path() -> Path:
    return _git_path("hooks")


def _commit_msg_hook_path() -> Path:
    return _git_path("hooks/commit-msg")


def _format_candidates(
    *,
    initially_staged: tuple[str, ...],
    initially_unstaged: tuple[str, ...],
) -> tuple[str, ...]:
    partially_staged = set(initially_staged) & set(initially_unstaged)
    candidates = [
        path
        for path in initially_staged
        if Path(path).suffix in PYTHON_SUFFIXES and path not in partially_staged
    ]
    return tuple(candidates)


def _run_command(command: list[str], *, env: dict[str, str] | None = None) -> int:
    return subprocess.run(command, check=False, env=env).returncode


def _log_command(command: list[str]) -> None:
    print(f"+ {shlex.join(command)}", file=sys.stderr)


def _run_pre_commit() -> int:
    env = os.environ.copy()
    command = [
        sys.executable,
        "-m",
        "pre_commit",
        "hook-impl",
        "--config=.pre-commit-config.yaml",
        "--hook-type=pre-commit",
        "--hook-dir",
        str(_hook_dir_path().resolve()),
        "--",
    ]
    return _run_command(command, env=env)


def _require_commit_message_hook() -> int:
    hook_path = _commit_msg_hook_path()
    if not hook_path.is_file():
        print(
            "repo commit-msg hook is not installed; run "
            '`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" '
            "uv run python -m tools.install_git_hooks`",
            file=sys.stderr,
        )
        return 1

    hook_text = hook_path.read_text(encoding="utf-8")
    if all(needle in hook_text for needle in _COMMIT_MSG_HOOK_NEEDLES):
        return 0

    print(
        "repo commit-msg hook is stale or invalid; run "
        '`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" '
        "uv run python -m tools.install_git_hooks`",
        file=sys.stderr,
    )
    return 1


def _format_and_stage(paths: tuple[str, ...]) -> int:
    if not paths:
        return 0
    print("running staged ruff autofixes before commit", file=sys.stderr)
    for command in (
        [sys.executable, "-m", "ruff", "check", "--fix", *paths],
        [sys.executable, "-m", "ruff", "format", *paths],
        ["git", "add", "--", *paths],
    ):
        _log_command(command)
        status = _run_command(command)
        if status != 0:
            return status
    return 0


def main(argv: list[str] | None = None) -> int:
    del argv
    hook_status = _require_commit_message_hook()
    if hook_status != 0:
        return hook_status
    initially_staged = _git_paths(
        "diff", "--cached", "--name-only", "--diff-filter=ACMR"
    )
    initially_unstaged = _git_paths("diff", "--name-only", "--diff-filter=ACMR")
    format_status = _format_and_stage(
        _format_candidates(
            initially_staged=initially_staged,
            initially_unstaged=initially_unstaged,
        )
    )
    if format_status != 0:
        return format_status
    return _run_pre_commit()


if __name__ == "__main__":
    raise SystemExit(main())
