from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkSuite:
    name: str
    description: str
    command: tuple[str, ...]


SUITES = (
    BenchmarkSuite(
        name="unit",
        description="Unit tests without coverage overhead.",
        command=("pytest", "tests/unit", "--no-cov", "-q", "--durations=10"),
    ),
    BenchmarkSuite(
        name="contract",
        description="Contract tests without coverage overhead.",
        command=("pytest", "tests/contract", "--no-cov", "-q", "--durations=10"),
    ),
    BenchmarkSuite(
        name="e2e",
        description="E2E CLI tests without coverage overhead.",
        command=("pytest", "tests/e2e", "--no-cov", "-q", "--durations=10"),
    ),
    BenchmarkSuite(
        name="full",
        description="Full test suite with project coverage requirements.",
        command=("pytest", "-q", "--durations=10"),
    ),
)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark pytest suite segments for this repo.")
    parser.add_argument(
        "--suite",
        action="append",
        choices=tuple(suite.name for suite in SUITES),
        help="Benchmark only the named suite. May be passed multiple times.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run each selected suite with pytest-xdist using -n auto.",
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def _selected_suites(selected_names: Sequence[str] | None) -> tuple[BenchmarkSuite, ...]:
    if not selected_names:
        return SUITES
    selected = set(selected_names)
    return tuple(suite for suite in SUITES if suite.name in selected)


def _command_for_suite(suite: BenchmarkSuite, *, parallel: bool) -> tuple[str, ...]:
    command = list(suite.command)
    if parallel:
        command[1:1] = ["-n", "auto"]
    return tuple(command)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    exit_code = 0

    for suite in _selected_suites(args.suite):
        command = _command_for_suite(suite, parallel=args.parallel)
        print(f"[suite:{suite.name}] {suite.description}", flush=True)
        print(f"[command] uv run {' '.join(command)}", flush=True)
        started = time.perf_counter()
        result = subprocess.run([sys.executable, "-m", "pytest", *command[1:]], check=False)
        elapsed = time.perf_counter() - started
        print(f"[result] exit={result.returncode} elapsed={elapsed:.2f}s")
        if result.returncode != 0:
            exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
