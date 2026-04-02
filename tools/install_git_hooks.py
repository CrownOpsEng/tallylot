from __future__ import annotations

import stat
import subprocess
from pathlib import Path

HOOK_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
cd "$REPO_ROOT"

PYTHON="$REPO_ROOT/.venv/bin/python3"
if [ -x "$PYTHON" ]; then
    exec "$PYTHON" -m tools.pre_commit_hook "$@"
elif command -v python3 > /dev/null; then
    exec python3 -m tools.pre_commit_hook "$@"
else
    echo 'python3 not found for repo pre-commit hook' 1>&2
    exit 1
fi
"""


def install_hooks(repo_root: Path) -> None:
    subprocess.run(
        ["git", "config", "--local", "commit.template", ".gitmessage.txt"],
        check=True,
        cwd=repo_root,
    )
    subprocess.run(
        [
            "uv",
            "run",
            "pre-commit",
            "install",
            "--overwrite",
            "--hook-type",
            "pre-commit",
            "--hook-type",
            "commit-msg",
        ],
        check=True,
        cwd=repo_root,
    )
    hook_path = repo_root / ".git/hooks/pre-commit"
    hook_path.write_text(HOOK_TEMPLATE, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> int:
    install_hooks(Path.cwd())
    print("Installed repo git hooks and commit template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
