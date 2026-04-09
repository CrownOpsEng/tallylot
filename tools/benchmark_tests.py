from __future__ import annotations

import argparse
import os
import subprocess
import time
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from repo_support.quality_gates import apply_gate_environment
from tools.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class BenchmarkSuite:
    name: str
    description: str
    command: tuple[str, ...]


SUITES = (
    BenchmarkSuite(
        name="unit",
        description="Unit tests without coverage overhead.",
        command=(
            "uv",
            "run",
            "pytest",
            "tests/unit",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="contract",
        description="Contract tests without coverage overhead.",
        command=(
            "uv",
            "run",
            "pytest",
            "tests/contract",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="e2e",
        description="E2E CLI tests without coverage overhead.",
        command=(
            "uv",
            "run",
            "pytest",
            "tests/e2e",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="full",
        description="Full test suite with project coverage requirements.",
        command=("uv", "run", "pytest", "-q", "--durations=10"),
    ),
)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark pytest suite segments for this repo."
    )
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


def _selected_suites(
    selected_names: Sequence[str] | None,
) -> tuple[BenchmarkSuite, ...]:
    if not selected_names:
        return SUITES
    selected = set(selected_names)
    return tuple(suite for suite in SUITES if suite.name in selected)


def _command_for_suite(suite: BenchmarkSuite, *, parallel: bool) -> tuple[str, ...]:
    command = list(suite.command)
    if parallel:
        command[3:3] = ["-n", "auto"]
    return tuple(command)


def _suite_environment(
    suite: BenchmarkSuite,
    *,
    coverage_file: Path | None = None,
) -> dict[str, str]:
    environment = repo_uv_environment()
    environment.pop("COVERAGE_PROCESS_START", None)
    environment.pop("COVERAGE_RCFILE", None)
    if "PYTEST_ADDOPTS" in os.environ and "PYTEST_ADDOPTS" not in environment:
        environment["PYTEST_ADDOPTS"] = os.environ["PYTEST_ADDOPTS"]
    return apply_gate_environment(
        environment,
        coverage_gate=suite.name == "full",
        coverage_file=coverage_file,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    exit_code = 0

    for suite in _selected_suites(args.suite):
        command = _command_for_suite(suite, parallel=args.parallel)
        print(f"[suite:{suite.name}] {suite.description}", flush=True)
        print(f"[command] {' '.join(command)}", flush=True)
        started = time.perf_counter()
        with ExitStack() as stack:
            temp_dir = (
                stack.enter_context(
                    TemporaryDirectory(
                        prefix=f"tallylot-benchmark-{suite.name}-coverage-"
                    )
                )
                if suite.name == "full"
                else None
            )
            coverage_file = Path(temp_dir) / ".coverage" if temp_dir else None
            result = subprocess.run(
                command,
                check=False,
                env=_suite_environment(suite, coverage_file=coverage_file),
            )
        elapsed = time.perf_counter() - started
        print(f"[result] exit={result.returncode} elapsed={elapsed:.2f}s")
        if result.returncode != 0:
            exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
