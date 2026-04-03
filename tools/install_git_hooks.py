from __future__ import annotations

import shlex
import stat
import subprocess
import sys
from pathlib import Path

from tools.uv_environment import default_project_environment, repo_uv_environment

_HOOK_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

PROJECT_ENVIRONMENT={project_environment}
if [ -n "$PROJECT_ENVIRONMENT" ]; then
    export UV_PROJECT_ENVIRONMENT="$PROJECT_ENVIRONMENT"
fi

PYTHON={python}
if [ -x "$PYTHON" ]; then
    exec "$PYTHON" -m tools.pre_commit_hook "$@"
elif command -v uv > /dev/null; then
    exec uv run python -m tools.pre_commit_hook "$@"
elif command -v python3 > /dev/null; then
    exec python3 -m tools.pre_commit_hook "$@"
else
    echo 'python3 not found for repo pre-commit hook' 1>&2
    exit 1
fi
"""

_COMMIT_MSG_HOOK_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

PROJECT_ENVIRONMENT={project_environment}
if [ -n "$PROJECT_ENVIRONMENT" ]; then
    export UV_PROJECT_ENVIRONMENT="$PROJECT_ENVIRONMENT"
fi

PYTHON={python}
if [ -x "$PYTHON" ]; then
    exec "$PYTHON" -m pre_commit hook-impl \
        --config=.pre-commit-config.yaml \
        --hook-type=commit-msg \
        --hook-dir "$HOOK_DIR" -- "$@"
elif command -v uv > /dev/null; then
    exec uv run python -m pre_commit hook-impl \
        --config=.pre-commit-config.yaml \
        --hook-type=commit-msg \
        --hook-dir "$HOOK_DIR" -- "$@"
elif command -v pre-commit > /dev/null; then
    exec pre-commit hook-impl \
        --config=.pre-commit-config.yaml \
        --hook-type=commit-msg \
        --hook-dir "$HOOK_DIR" -- "$@"
else
    echo '`pre-commit` not found. Did you forget to activate your virtualenv?' 1>&2
    exit 1
fi
"""


def _installed_project_environment() -> str | None:
    if sys.prefix == sys.base_prefix:
        return None
    return str(Path(sys.executable).parent.parent)


def _hook_project_environment() -> str:
    return _installed_project_environment() or default_project_environment()


def _install_hooks(repo_root: Path) -> None:
    subprocess.run(
        ["git", "config", "--local", "commit.template", ".gitmessage.txt"],
        check=True,
        cwd=repo_root,
    )
    subprocess.run(
        ["uv", "sync", "--frozen"],
        check=True,
        cwd=repo_root,
        env=repo_uv_environment(),
    )
    hook_format_args = {
        "project_environment": shlex.quote(_hook_project_environment()),
        "python": shlex.quote(sys.executable),
    }
    hook_path = repo_root / ".git/hooks/pre-commit"
    hook_path.write_text(
        _HOOK_TEMPLATE.format(**hook_format_args),
        encoding="utf-8",
    )
    hook_path.chmod(
        hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )
    commit_msg_hook_path = repo_root / ".git/hooks/commit-msg"
    commit_msg_hook_path.write_text(
        _COMMIT_MSG_HOOK_TEMPLATE.format(**hook_format_args),
        encoding="utf-8",
    )
    commit_msg_hook_path.chmod(
        commit_msg_hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )


def main() -> int:
    _install_hooks(Path.cwd())
    print("Installed repo git hooks and commit template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
