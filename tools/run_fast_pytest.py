from __future__ import annotations

import subprocess
from collections.abc import Sequence

from repo_support.pytest_commands import build_fast_pytest_command
from repo_support.uv_environment import repo_uv_environment


def _command() -> tuple[str, ...]:
    return build_fast_pytest_command()


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    return subprocess.run(
        _command(),
        check=False,
        env=repo_uv_environment(),
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
