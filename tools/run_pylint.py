from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from repo_support.paths import repo_root
from repo_support.pyright_config import adapter_test_roots


@dataclass(frozen=True)
class _PylintTarget:
    name: str
    command: tuple[str, ...]


_ADAPTER_TEST_IGNORE_PATHS = r"^src/tallylot/adapters/.*/tests(/.*)?$"


def _pylint_targets(*, root: Path | None = None) -> tuple[_PylintTarget, ...]:
    active_root = repo_root() if root is None else root.expanduser().resolve()
    return (
        _PylintTarget(
            name="src-tools",
            command=(
                sys.executable,
                "-m",
                "pylint",
                f"--ignore-paths={_ADAPTER_TEST_IGNORE_PATHS}",
                "src",
                "tools",
                "conftest.py",
            ),
        ),
        _PylintTarget(
            name="tests",
            command=(
                sys.executable,
                "-m",
                "pylint",
                "--rcfile=.pylintrc-tests",
                "tests",
                *adapter_test_roots(root=active_root),
            ),
        ),
    )


def _run_target(target: _PylintTarget) -> int:
    result = subprocess.run(target.command, check=False)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    exit_code = 0
    for target in _pylint_targets():
        print(f"[pylint:{target.name}] {' '.join(target.command[2:])}", flush=True)
        if _run_target(target) != 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
