from __future__ import annotations

import argparse
import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class BenchmarkStrategy:
    name: str
    description: str
    command: tuple[str, ...]


STRATEGIES = (
    BenchmarkStrategy(
        name="fast-current",
        description="Current fast-gate baseline with all checks started together.",
        command=(
            "uv",
            "run",
            "python",
            "-m",
            "tools.run_quality_gates",
            "--schedule",
            "all-at-once",
        ),
    ),
    BenchmarkStrategy(
        name="fast-optimized",
        description="Repo-benchmarked fast-gate schedule.",
        command=("uv", "run", "python", "-m", "tools.run_quality_gates"),
    ),
    BenchmarkStrategy(
        name="full-current",
        description="Current full-gate baseline with all checks started together.",
        command=(
            "uv",
            "run",
            "python",
            "-m",
            "tools.run_quality_gates",
            "--full-tests",
            "--schedule",
            "all-at-once",
        ),
    ),
    BenchmarkStrategy(
        name="full-phased",
        description="Alternative phased full-gate schedule for comparison.",
        command=(
            "uv",
            "run",
            "python",
            "-m",
            "tools.run_quality_gates",
            "--full-tests",
            "--schedule",
            "phased",
        ),
    ),
)


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark quality gate scheduling strategies for this repo."
    )
    parser.add_argument(
        "--strategy",
        action="append",
        choices=tuple(strategy.name for strategy in STRATEGIES),
        help="Benchmark only the named strategy. May be passed multiple times.",
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def _selected_strategies(
    selected_names: Sequence[str] | None,
) -> tuple[BenchmarkStrategy, ...]:
    if not selected_names:
        return STRATEGIES
    selected = set(selected_names)
    return tuple(strategy for strategy in STRATEGIES if strategy.name in selected)


def _clean_runtime_artifacts() -> None:
    for path in Path.cwd().glob(".coverage*"):
        if path.is_file():
            path.unlink()


def _benchmark_environment() -> dict[str, str]:
    environment = repo_uv_environment()
    environment.pop("COVERAGE_PROCESS_START", None)
    environment.pop("COVERAGE_RCFILE", None)
    if "PYTEST_ADDOPTS" in os.environ and "PYTEST_ADDOPTS" not in environment:
        environment["PYTEST_ADDOPTS"] = os.environ["PYTEST_ADDOPTS"]
    return environment


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    exit_code = 0

    for strategy in _selected_strategies(args.strategy):
        _clean_runtime_artifacts()
        print(f"[strategy:{strategy.name}] {strategy.description}", flush=True)
        print(f"[command] {' '.join(strategy.command)}", flush=True)
        started = time.perf_counter()
        result = subprocess.run(
            strategy.command,
            check=False,
            env=_benchmark_environment(),
        )
        elapsed = time.perf_counter() - started
        print(f"[result] exit={result.returncode} elapsed={elapsed:.2f}s", flush=True)
        if result.returncode != 0:
            exit_code = result.returncode

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
