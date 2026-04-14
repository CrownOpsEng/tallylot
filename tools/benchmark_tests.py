from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory

from repo_support.quality_gates import apply_gate_environment
from repo_support.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class BenchmarkSuite:
    name: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkMeasurement:
    kind: str
    iteration: int
    returncode: int
    elapsed: float


@dataclass(frozen=True)
class BenchmarkSummary:
    suite: BenchmarkSuite
    warmup_count: int
    measured_iterations: int
    measurements: tuple[BenchmarkMeasurement, ...]

    @property
    def measured_measurements(self) -> tuple[BenchmarkMeasurement, ...]:
        return tuple(
            measurement
            for measurement in self.measurements
            if measurement.kind == "measured"
        )

    @property
    def median_elapsed(self) -> float:
        return median(measurement.elapsed for measurement in self.measured_measurements)

    @property
    def measured_elapsed(self) -> tuple[float, ...]:
        return tuple(measurement.elapsed for measurement in self.measured_measurements)

    @property
    def exit_code(self) -> int:
        return max(
            (measurement.returncode for measurement in self.measurements), default=0
        )


SUITES = (
    BenchmarkSuite(
        name="fast-unit-serial",
        description="Fast unit slice without xdist.",
        command=(
            "uv",
            "run",
            "pytest",
            "-m",
            "unit and not slow",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="fast-unit-n4",
        description="Fast unit slice with a fixed four-worker xdist pool.",
        command=(
            "uv",
            "run",
            "pytest",
            "-n",
            "4",
            "-m",
            "unit and not slow",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="fast-unit-nauto",
        description="Fast unit slice with pytest-xdist auto worker selection.",
        command=(
            "uv",
            "run",
            "pytest",
            "-n",
            "auto",
            "-m",
            "unit and not slow",
            "--no-cov",
            "-q",
            "--durations=10",
        ),
    ),
    BenchmarkSuite(
        name="full-serial",
        description="Full test suite with coverage and no xdist.",
        command=("uv", "run", "pytest", "-q", "--durations=10"),
    ),
    BenchmarkSuite(
        name="full-nauto",
        description="Full test suite with coverage and pytest-xdist auto workers.",
        command=("uv", "run", "pytest", "-n", "auto", "-q", "--durations=10"),
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
        "--warmup-count",
        type=int,
        default=1,
        help="Number of warmup runs to execute before measured iterations.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of measured iterations to execute per selected suite.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for a JSON benchmark summary.",
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
        coverage_gate=suite.name.startswith("full"),
        coverage_file=coverage_file,
    )


def _validate_args(args: argparse.Namespace) -> None:
    if args.warmup_count < 0:
        raise ValueError("--warmup-count must be zero or greater")
    if args.iterations < 1:
        raise ValueError("--iterations must be at least 1")


def _run_measurement(
    suite: BenchmarkSuite,
    *,
    kind: str,
    iteration: int,
) -> BenchmarkMeasurement:
    started = time.perf_counter()
    with ExitStack() as stack:
        temp_dir = (
            stack.enter_context(
                TemporaryDirectory(prefix=f"tallylot-benchmark-{suite.name}-coverage-")
            )
            if suite.name.startswith("full")
            else None
        )
        coverage_file = Path(temp_dir) / ".coverage" if temp_dir else None
        result = subprocess.run(
            suite.command,
            check=False,
            env=_suite_environment(suite, coverage_file=coverage_file),
        )
    elapsed = time.perf_counter() - started
    print(
        f"[{kind}:{suite.name}:{iteration}] exit={result.returncode} "
        f"elapsed={elapsed:.2f}s",
        flush=True,
    )
    return BenchmarkMeasurement(
        kind=kind,
        iteration=iteration,
        returncode=result.returncode,
        elapsed=elapsed,
    )


def _benchmark_suite(
    suite: BenchmarkSuite,
    *,
    warmup_count: int,
    measured_iterations: int,
) -> BenchmarkSummary:
    print(f"[suite:{suite.name}] {suite.description}", flush=True)
    print(f"[command] {' '.join(suite.command)}", flush=True)
    measurements: list[BenchmarkMeasurement] = []
    for iteration in range(1, warmup_count + 1):
        measurements.append(_run_measurement(suite, kind="warmup", iteration=iteration))
    for iteration in range(1, measured_iterations + 1):
        measurements.append(
            _run_measurement(suite, kind="measured", iteration=iteration)
        )
    summary = BenchmarkSummary(
        suite=suite,
        warmup_count=warmup_count,
        measured_iterations=measured_iterations,
        measurements=tuple(measurements),
    )
    measured_elapsed = ", ".join(
        f"{elapsed:.2f}" for elapsed in summary.measured_elapsed
    )
    print(
        f"[summary:{suite.name}] median={summary.median_elapsed:.2f}s "
        f"measured=[{measured_elapsed}]",
        flush=True,
    )
    return summary


def _summary_payload(summary: BenchmarkSummary) -> dict[str, object]:
    return {
        "name": summary.suite.name,
        "description": summary.suite.description,
        "command": list(summary.suite.command),
        "warmup_count": summary.warmup_count,
        "measured_iterations": summary.measured_iterations,
        "median_elapsed_seconds": summary.median_elapsed,
        "measured_elapsed_seconds": list(summary.measured_elapsed),
        "measurements": [
            {
                "kind": measurement.kind,
                "iteration": measurement.iteration,
                "returncode": measurement.returncode,
                "elapsed_seconds": measurement.elapsed,
            }
            for measurement in summary.measurements
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        _validate_args(args)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    summaries = [
        _benchmark_suite(
            suite,
            warmup_count=args.warmup_count,
            measured_iterations=args.iterations,
        )
        for suite in _selected_suites(args.suite)
    ]
    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(
                {
                    "warmup_count": args.warmup_count,
                    "measured_iterations": args.iterations,
                    "suites": [_summary_payload(summary) for summary in summaries],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return max((summary.exit_code for summary in summaries), default=0)


if __name__ == "__main__":
    raise SystemExit(main())
