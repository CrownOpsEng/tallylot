from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass

from repo_support.local_autofix import run_local_autofix
from repo_support.quality_gates import (
    QUALITY_GATE_ORDER,
    QUALITY_SCHEDULES,
    QualityGate,
    QualityPhase,
    apply_gate_environment,
    available_quality_gates,
    quality_phase_plan,
)
from repo_support.pyright_config import sync_pyright_config
from tools.uv_environment import repo_uv_environment


@dataclass(frozen=True)
class GateResult:
    gate: QualityGate
    returncode: int
    stdout: str
    stderr: str
    elapsed: float


@dataclass(frozen=True)
class PhaseResult:
    phase: QualityPhase
    gate_results: tuple[GateResult, ...]


@dataclass(frozen=True)
class RunSummary:
    phase_results: tuple[PhaseResult, ...]
    total_elapsed: float


@dataclass(frozen=True)
class _RunRequest:
    name: str
    full_tests: bool
    schedule: str
    selected_gate_names: tuple[str, ...]
    fail_fast: bool
    auto_fix: bool


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local quality gates.")
    parser.add_argument(
        "--full-tests",
        action="store_true",
        help="Run the full pytest suite instead of the fast commit-time subset.",
    )
    parser.add_argument(
        "--gate",
        action="append",
        choices=QUALITY_GATE_ORDER,
        help="Run only the named quality gate. May be passed multiple times.",
    )
    parser.add_argument(
        "--schedule",
        choices=QUALITY_SCHEDULES,
        default="auto",
        help=(
            "Quality gate scheduling strategy. `auto` uses the repo-benchmarked "
            "default for the selected test mode."
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failing phase and skip the remaining phases.",
    )
    parser.add_argument(
        "--no-auto-fix",
        action="store_true",
        help="Skip the local safe autofix step before running validation gates.",
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def _run_request(args: argparse.Namespace) -> _RunRequest:
    selected_gate_names = tuple(args.gate or ())
    return _RunRequest(
        name="full" if args.full_tests else "fast",
        full_tests=args.full_tests,
        schedule=args.schedule,
        selected_gate_names=selected_gate_names,
        fail_fast=args.fail_fast,
        auto_fix=not args.no_auto_fix,
    )


def _phase_plan(run_request: _RunRequest) -> tuple[QualityPhase, ...]:
    return quality_phase_plan(
        full_tests=run_request.full_tests,
        schedule=run_request.schedule,
        selected_gate_names=run_request.selected_gate_names or None,
    )


def _run_gate(gate: QualityGate) -> GateResult:
    started = time.perf_counter()
    result = subprocess.run(
        gate.command,
        capture_output=True,
        text=True,
        check=False,
        env=_gate_environment(gate),
    )
    return GateResult(
        gate=gate,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        elapsed=time.perf_counter() - started,
    )


def _gate_environment(
    gate: QualityGate,
) -> dict[str, str]:
    return apply_gate_environment(
        repo_uv_environment(),
        coverage_gate=gate.coverage_gate,
    )


def _print_gate_result(gate_result: GateResult) -> None:
    print(
        f"[{gate_result.gate.name}] exit={gate_result.returncode} "
        f"elapsed={gate_result.elapsed:.2f}s"
    )
    if gate_result.stdout:
        print(gate_result.stdout.rstrip())
    if gate_result.stderr:
        print(gate_result.stderr.rstrip())


def _run_phase(
    phase: QualityPhase,
    *,
    available_gates: dict[str, QualityGate],
) -> PhaseResult:
    print(f"[phase:{phase.name}] gates={', '.join(phase.gate_names)}", flush=True)
    gates = tuple(available_gates[gate_name] for gate_name in phase.gate_names)
    if not gates:
        return PhaseResult(phase=phase, gate_results=())

    with ThreadPoolExecutor(max_workers=len(gates)) as executor:
        future_by_gate_name = {
            gate.name: executor.submit(_run_gate, gate) for gate in gates
        }
        ordered_results = tuple(
            future_by_gate_name[gate.name].result() for gate in gates
        )
    for gate_result in ordered_results:
        _print_gate_result(gate_result)
    return PhaseResult(phase=phase, gate_results=ordered_results)


def _print_summary(summary: RunSummary) -> None:
    print("[summary] quality gate phases", flush=True)
    for phase_result in summary.phase_results:
        failures = sum(
            1
            for gate_result in phase_result.gate_results
            if gate_result.returncode != 0
        )
        phase_elapsed = max(
            (gate_result.elapsed for gate_result in phase_result.gate_results),
            default=0.0,
        )
        gate_names = ", ".join(
            gate_result.gate.name for gate_result in phase_result.gate_results
        )
        print(
            f"[summary:{phase_result.phase.name}] gates={gate_names} "
            f"failures={failures} elapsed~={phase_elapsed:.2f}s"
        )
    print(f"[summary] total elapsed={summary.total_elapsed:.2f}s")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    run_request = _run_request(args)
    if sync_pyright_config():
        print(
            "[pyright-config] pyrightconfig.tests.json was out of sync and has "
            "been refreshed; review and commit it before rerunning quality gates",
            flush=True,
        )
        return 1
    if run_request.auto_fix:
        autofix_status = run_local_autofix()
        if autofix_status != 0:
            return autofix_status

    available_gates = available_quality_gates(full_tests=run_request.full_tests)
    phase_results: list[PhaseResult] = []
    started = time.perf_counter()
    stop_after_failure = False
    for phase in _phase_plan(run_request):
        if stop_after_failure:
            break
        phase_result = _run_phase(phase, available_gates=available_gates)
        phase_results.append(phase_result)
        phase_failed = any(
            gate_result.returncode != 0 for gate_result in phase_result.gate_results
        )
        if phase_failed and run_request.fail_fast:
            stop_after_failure = True

    summary = RunSummary(
        phase_results=tuple(phase_results),
        total_elapsed=time.perf_counter() - started,
    )
    _print_summary(summary)
    return (
        1
        if any(
            gate_result.returncode != 0
            for phase_result in summary.phase_results
            for gate_result in phase_result.gate_results
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
