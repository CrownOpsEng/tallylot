from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from repo_support.local_autofix import run_local_autofix
from repo_support.review_verification import (
    CheckExecutionContext,
    build_verification_plan,
    changed_paths,
    run_plan,
)

REVIEW_LOOP_REMINDER = (
    "review reminder: passing verification does not complete the mandatory "
    "red-team repair loop, decide the pass outcome, or authorize PR readiness"
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repo-native PR review checks for the current diff."
    )
    parser.add_argument("--base-sha", help="Base commit SHA for the diff range.")
    parser.add_argument("--head-sha", help="Head commit SHA for the diff range.")
    parser.add_argument(
        "--trigger",
        choices=("pull_request", "push_main", "local"),
        default="local",
        help="Verification trigger to model.",
    )
    parser.add_argument(
        "--mode",
        choices=("planned", "full"),
        default="planned",
        help="Verification selection mode.",
    )
    parser.add_argument("--branch-name", help="Branch name override.")
    parser.add_argument("--pr-title", help="Pull request title override.")
    parser.add_argument("--pr-body-file", help="Pull request body file override.")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failing blocking check.",
    )
    parser.add_argument(
        "--no-auto-fix",
        action="store_true",
        help="Skip the local safe autofix step before running review checks.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if (args.base_sha is None) != (args.head_sha is None):
        print(
            "provide both --base-sha and --head-sha when overriding the diff range",
            file=sys.stderr,
        )
        return 2

    plan = build_verification_plan(
        paths=changed_paths(base_sha=args.base_sha, head_sha=args.head_sha),
        trigger=args.trigger,
        mode=args.mode,
    )
    if plan.surface_report.unmapped_paths:
        print(
            "pr review checks failed: changed paths are not mapped to repo review surfaces",
            file=sys.stderr,
        )
        for path in plan.surface_report.unmapped_paths:
            print(f"  - {path}", file=sys.stderr)
        return 1
    if not plan.surface_report.changed_paths:
        print("no changed paths detected")
        return 0

    print(REVIEW_LOOP_REMINDER)
    if not args.no_auto_fix:
        autofix_status = run_local_autofix()
        if autofix_status != 0:
            return autofix_status
    pr_body = None
    if args.pr_body_file is not None:
        pr_body = Path(args.pr_body_file).read_text(encoding="utf-8")
    summary = run_plan(
        plan,
        context=CheckExecutionContext(
            trigger=args.trigger,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            branch_name=args.branch_name,
            pr_title=args.pr_title,
            pr_body=pr_body,
        ),
        fail_fast=args.fail_fast,
    )
    print(
        "verification complete: use this evidence in the current issue-finding "
        "pass, then go look for the next real issues"
    )
    return 1 if summary.has_blocking_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
