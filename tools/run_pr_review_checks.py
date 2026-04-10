from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass

from repo_support.pr_review import PrReviewPlan, changed_paths, classify_changed_paths
from tools.uv_environment import repo_uv_environment

REVIEW_LOOP_REMINDER = (
    "review reminder: passing verification does not complete the mandatory "
    "red-team repair loop or authorize PR readiness"
)


@dataclass(frozen=True)
class ReviewCheckStep:
    name: str
    command: tuple[str, ...]
    blocking: bool = True


def _verification_note(plan: PrReviewPlan) -> str | None:
    if plan.verification_level == "ci-parity" and plan.requires_full_quality_gates:
        return (
            "verification note: ci-parity is the broad runner for this diff and "
            "already includes the full quality, build, and wheel parity path, "
            "so duplicate quality-gates-full is intentionally skipped"
        )
    return None


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repo-native PR review checks for the current diff."
    )
    parser.add_argument("--base-sha", help="Base commit SHA for the diff range.")
    parser.add_argument("--head-sha", help="Head commit SHA for the diff range.")
    return parser.parse_args(argv)


def _steps_for_plan(plan: PrReviewPlan) -> tuple[ReviewCheckStep, ...]:
    steps = [
        ReviewCheckStep(name=check.name, command=check.command)
        for check in plan.targeted_checks
    ]
    if plan.verification_level == "quality-gates-full":
        steps.append(
            ReviewCheckStep(
                name="quality-gates-full",
                command=(
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "tools.run_quality_gates",
                    "--full-tests",
                ),
            )
        )
    if plan.verification_level == "ci-parity":
        steps.append(
            ReviewCheckStep(
                name="ci-parity",
                command=("uv", "run", "python", "-m", "tools.run_ci_parity_checks"),
            )
        )
    if plan.requires_test_stress_checks:
        steps.append(
            ReviewCheckStep(
                name="test-stress-checks",
                command=("uv", "run", "python", "-m", "tools.run_test_stress_checks"),
            )
        )
    if plan.requires_pre_merge_packaging_verification:
        steps.append(
            ReviewCheckStep(
                name="pre-merge-packaging",
                command=(
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "tools.run_ci_parity_checks",
                    "--step",
                    "build",
                    "--step",
                    "verify-wheel",
                ),
            )
        )
    if plan.requires_coverage_hotspot_report:
        steps.append(
            ReviewCheckStep(
                name="coverage-hotspots",
                command=("uv", "run", "python", "-m", "tools.report_coverage_hotspots"),
                blocking=False,
            )
        )
    return tuple(steps)


def _run_step(step: ReviewCheckStep) -> int:
    started = time.perf_counter()
    result = subprocess.run(
        step.command,
        capture_output=True,
        text=True,
        check=False,
        env=repo_uv_environment(),
    )
    elapsed = time.perf_counter() - started
    print(f"[{step.name}] exit={result.returncode} elapsed={elapsed:.2f}s")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    return result.returncode


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if (args.base_sha is None) != (args.head_sha is None):
        print(
            "provide both --base-sha and --head-sha when overriding the diff range",
            file=sys.stderr,
        )
        return 2

    plan = classify_changed_paths(
        changed_paths(base_sha=args.base_sha, head_sha=args.head_sha)
    )
    if plan.unmapped_paths:
        print(
            "pr review checks failed: changed paths are not mapped to repo review surfaces",
            file=sys.stderr,
        )
        for path in plan.unmapped_paths:
            print(f"  - {path}", file=sys.stderr)
        return 1
    if not plan.changed_paths:
        print("no changed paths detected")
        return 0

    print(REVIEW_LOOP_REMINDER)
    verification_note = _verification_note(plan)
    if verification_note is not None:
        print(verification_note)
    for step in _steps_for_plan(plan):
        returncode = _run_step(step)
        if returncode != 0 and step.blocking:
            return 1
        if returncode != 0 and not step.blocking:
            print(f"[{step.name}] non-blocking failure; continuing", flush=True)
    print(
        "verification complete: continue the red-team review loop before calling the pass clean"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
