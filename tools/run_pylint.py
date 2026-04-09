from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from repo_support.paths import repo_root
from repo_support.pyright_config import adapter_test_roots


@dataclass(frozen=True)
class _PylintTarget:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class _PylintResult:
    target: _PylintTarget
    returncode: int
    stdout: str
    stderr: str
    elapsed: float


_ADAPTER_TEST_IGNORE_PATHS = r"^src/tallylot/adapters/.*/tests(/.*)?$"


def _pylint_targets(*, root: Path | None = None) -> tuple[_PylintTarget, ...]:
    active_root = repo_root() if root is None else root.expanduser().resolve()
    return (
        _PylintTarget(
            name="repo-code",
            command=(
                sys.executable,
                "-m",
                "pylint",
                f"--ignore-paths={_ADAPTER_TEST_IGNORE_PATHS}",
                "src",
                "tools",
                "repo_support",
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


def _run_target(target: _PylintTarget) -> _PylintResult:
    started = time.perf_counter()
    result = subprocess.run(
        target.command,
        check=False,
        capture_output=True,
        text=True,
    )
    return _PylintResult(
        target=target,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        elapsed=time.perf_counter() - started,
    )


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    exit_code = 0
    targets = _pylint_targets()
    with ThreadPoolExecutor(max_workers=len(targets)) as executor:
        futures = {executor.submit(_run_target, target): target for target in targets}
        for future in as_completed(futures):
            result = future.result()
            print(
                f"[pylint:{result.target.name}] exit={result.returncode} "
                f"elapsed={result.elapsed:.2f}s"
            )
            print(
                f"[pylint:{result.target.name}:command] "
                f"{' '.join(result.target.command[2:])}",
                flush=True,
            )
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip())
            if result.returncode != 0:
                exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
