from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median

from repo_support.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class BenchmarkStrategy:
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
    strategy: BenchmarkStrategy
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


STRATEGIES = (
    BenchmarkStrategy(
        name="fast-current",
        description="Default fast-gate schedule with all checks started together.",
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
        description="Alternative phased fast-gate schedule for comparison.",
        command=(
            "uv",
            "run",
            "python",
            "-m",
            "tools.run_quality_gates",
            "--schedule",
            "phased",
        ),
    ),
    BenchmarkStrategy(
        name="full-current",
        description="Default full-gate schedule with all checks started together.",
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
        help="Number of measured iterations to execute per selected strategy.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path for a JSON benchmark summary.",
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


def _benchmark_environment() -> dict[str, str]:
    environment = repo_uv_environment()
    environment.pop("COVERAGE_PROCESS_START", None)
    environment.pop("COVERAGE_RCFILE", None)
    if "PYTEST_ADDOPTS" in os.environ and "PYTEST_ADDOPTS" not in environment:
        environment["PYTEST_ADDOPTS"] = os.environ["PYTEST_ADDOPTS"]
    return environment


def _validate_args(args: argparse.Namespace) -> None:
    if args.warmup_count < 0:
        raise ValueError("--warmup-count must be zero or greater")
    if args.iterations < 1:
        raise ValueError("--iterations must be at least 1")


def _run_measurement(
    strategy: BenchmarkStrategy,
    *,
    kind: str,
    iteration: int,
) -> BenchmarkMeasurement:
    started = time.perf_counter()
    result = subprocess.run(
        strategy.command,
        check=False,
        env=_benchmark_environment(),
    )
    elapsed = time.perf_counter() - started
    print(
        f"[{kind}:{strategy.name}:{iteration}] exit={result.returncode} "
        f"elapsed={elapsed:.2f}s",
        flush=True,
    )
    return BenchmarkMeasurement(
        kind=kind,
        iteration=iteration,
        returncode=result.returncode,
        elapsed=elapsed,
    )


def _benchmark_strategy(
    strategy: BenchmarkStrategy,
    *,
    warmup_count: int,
    measured_iterations: int,
) -> BenchmarkSummary:
    print(f"[strategy:{strategy.name}] {strategy.description}", flush=True)
    print(f"[command] {' '.join(strategy.command)}", flush=True)
    measurements: list[BenchmarkMeasurement] = []
    for iteration in range(1, warmup_count + 1):
        measurements.append(
            _run_measurement(strategy, kind="warmup", iteration=iteration)
        )
    for iteration in range(1, measured_iterations + 1):
        measurements.append(
            _run_measurement(strategy, kind="measured", iteration=iteration)
        )
    summary = BenchmarkSummary(
        strategy=strategy,
        warmup_count=warmup_count,
        measured_iterations=measured_iterations,
        measurements=tuple(measurements),
    )
    measured_elapsed = ", ".join(
        f"{elapsed:.2f}" for elapsed in summary.measured_elapsed
    )
    print(
        f"[summary:{strategy.name}] median={summary.median_elapsed:.2f}s "
        f"measured=[{measured_elapsed}]",
        flush=True,
    )
    return summary


def _summary_payload(summary: BenchmarkSummary) -> dict[str, object]:
    return {
        "name": summary.strategy.name,
        "description": summary.strategy.description,
        "command": list(summary.strategy.command),
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
        _benchmark_strategy(
            strategy,
            warmup_count=args.warmup_count,
            measured_iterations=args.iterations,
        )
        for strategy in _selected_strategies(args.strategy)
    ]
    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(
                {
                    "warmup_count": args.warmup_count,
                    "measured_iterations": args.iterations,
                    "strategies": [_summary_payload(summary) for summary in summaries],
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
