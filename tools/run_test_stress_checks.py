from __future__ import annotations

import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

from repo_support.pytest_commands import build_fast_pytest_command
from tools.uv_environment import repo_uv_environment

FAST_STRESS_WORKERS = 4
PRIMARY_RANDOM_SEED = 1729
SECONDARY_RANDOM_SEED = 8191


@dataclass(frozen=True)
class StressStep:
    name: str
    marker_expression: str
    command: tuple[str, ...]
    serial_fallback_command: tuple[str, ...]
    seed: int
    workers: int


def _marker_pytest_command(
    marker_expression: str,
    *,
    seed: int,
    workers: int,
) -> tuple[str, ...]:
    if marker_expression == "unit and not slow":
        command = list(build_fast_pytest_command(workers=workers))
    else:
        command = ["uv", "run", "pytest"]
        if workers > 0:
            command.extend(("-n", str(workers)))
        command.extend(("-m", marker_expression, "--no-cov", "-q"))
    command.extend(("--randomly-seed", str(seed)))
    return tuple(command)


def _stress_steps() -> tuple[StressStep, ...]:
    return (
        StressStep(
            name="fast-unit-seed-a",
            marker_expression="unit and not slow",
            command=_marker_pytest_command(
                "unit and not slow",
                seed=PRIMARY_RANDOM_SEED,
                workers=FAST_STRESS_WORKERS,
            ),
            serial_fallback_command=_marker_pytest_command(
                "unit and not slow",
                seed=PRIMARY_RANDOM_SEED,
                workers=0,
            ),
            seed=PRIMARY_RANDOM_SEED,
            workers=FAST_STRESS_WORKERS,
        ),
        StressStep(
            name="fast-unit-seed-b",
            marker_expression="unit and not slow",
            command=_marker_pytest_command(
                "unit and not slow",
                seed=SECONDARY_RANDOM_SEED,
                workers=FAST_STRESS_WORKERS,
            ),
            serial_fallback_command=_marker_pytest_command(
                "unit and not slow",
                seed=SECONDARY_RANDOM_SEED,
                workers=0,
            ),
            seed=SECONDARY_RANDOM_SEED,
            workers=FAST_STRESS_WORKERS,
        ),
        StressStep(
            name="contract-seed-a",
            marker_expression="contract",
            command=_marker_pytest_command(
                "contract", seed=PRIMARY_RANDOM_SEED, workers=0
            ),
            serial_fallback_command=_marker_pytest_command(
                "contract", seed=PRIMARY_RANDOM_SEED, workers=0
            ),
            seed=PRIMARY_RANDOM_SEED,
            workers=0,
        ),
        StressStep(
            name="e2e-seed-a",
            marker_expression="e2e",
            command=_marker_pytest_command("e2e", seed=PRIMARY_RANDOM_SEED, workers=0),
            serial_fallback_command=_marker_pytest_command(
                "e2e", seed=PRIMARY_RANDOM_SEED, workers=0
            ),
            seed=PRIMARY_RANDOM_SEED,
            workers=0,
        ),
    )


def _print_reproduction(step: StressStep) -> None:
    print("[repro] rerun the failing stress step:", flush=True)
    print(f"[repro] {' '.join(step.command)}", flush=True)
    print(
        f"[repro] workers={step.workers} seed={step.seed} "
        f"marker={step.marker_expression}",
        flush=True,
    )
    print("[repro] serial fallback:", flush=True)
    print(f"[repro] {' '.join(step.serial_fallback_command)}", flush=True)


def _run_step(step: StressStep) -> int:
    started = time.perf_counter()
    result = subprocess.run(
        step.command,
        capture_output=True,
        text=True,
        check=False,
        env=repo_uv_environment(),
    )
    elapsed = time.perf_counter() - started
    print(f"[{step.name}] exit={result.returncode} elapsed={elapsed:.2f}s", flush=True)
    if result.stdout:
        print(result.stdout.rstrip(), flush=True)
    if result.stderr:
        print(result.stderr.rstrip(), flush=True)
    if result.returncode != 0:
        _print_reproduction(step)
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    for step in _stress_steps():
        if _run_step(step) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
