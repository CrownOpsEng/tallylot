from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PylintTarget:
    name: str
    command: tuple[str, ...]


TARGETS = (
    PylintTarget(
        name="src-tools",
        command=(sys.executable, "-m", "pylint", "src", "tools", "conftest.py"),
    ),
    PylintTarget(
        name="tests",
        command=(sys.executable, "-m", "pylint", "--disable=protected-access", "tests"),
    ),
)


def _run_target(target: PylintTarget) -> int:
    result = subprocess.run(target.command, check=False)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    exit_code = 0
    for target in TARGETS:
        print(f"[pylint:{target.name}] {' '.join(target.command[2:])}", flush=True)
        if _run_target(target) != 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
