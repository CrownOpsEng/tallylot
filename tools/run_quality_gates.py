from __future__ import annotations

import argparse
import subprocess
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from tools.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class QualityGate:
    name: str
    command: tuple[str, ...]


DEFAULT_TEST_COMMAND = ("uv", "run", "pytest", "-m", "unit and not slow", "--no-cov", "-q")
FULL_TEST_COMMAND = ("uv", "run", "pytest")


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local quality gates in parallel.")
    parser.add_argument(
        "--full-tests",
        action="store_true",
        help="Run the full pytest suite instead of the fast commit-time subset.",
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def _quality_gates(*, full_tests: bool) -> tuple[QualityGate, ...]:
    test_command = FULL_TEST_COMMAND if full_tests else DEFAULT_TEST_COMMAND
    return (
        QualityGate(name="markdownlint", command=("uv", "run", "pre-commit", "run", "markdownlint", "--all-files")),
        QualityGate(name="actionlint", command=("uv", "run", "actionlint", "-color")),
        QualityGate(name="ruff", command=("uv", "run", "ruff", "check", ".")),
        QualityGate(name="mypy", command=("uv", "run", "mypy")),
        QualityGate(name="pyright", command=("uv", "run", "pyright")),
        QualityGate(name="pylint", command=("uv", "run", "python", "-m", "tools.run_pylint")),
        QualityGate(name="pytest", command=test_command),
    )


def _run_gate(gate: QualityGate) -> tuple[QualityGate, subprocess.CompletedProcess[str], float]:
    started = time.perf_counter()
    result = subprocess.run(
        gate.command,
        capture_output=True,
        text=True,
        check=False,
        env=repo_uv_environment(),
    )
    return gate, result, time.perf_counter() - started


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    failures = 0
    quality_gates = _quality_gates(full_tests=args.full_tests)

    with ThreadPoolExecutor(max_workers=len(quality_gates)) as executor:
        futures = {executor.submit(_run_gate, gate): gate for gate in quality_gates}
        for future in as_completed(futures):
            gate, result, elapsed = future.result()
            print(f"[{gate.name}] exit={result.returncode} elapsed={elapsed:.2f}s")
            if result.stdout:
                print(result.stdout.rstrip())
            if result.stderr:
                print(result.stderr.rstrip())
            if result.returncode != 0:
                failures = 1

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
