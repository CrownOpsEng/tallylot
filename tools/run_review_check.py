from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from repo_support.review_verification import (
    CheckExecutionContext,
    check_spec,
    run_check,
)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one review verification check.")
    parser.add_argument("--check-id", required=True, help="Atomic check id to run.")
    parser.add_argument(
        "--trigger",
        choices=("pull_request", "push_main", "local"),
        default="local",
        help="Verification trigger context for the check.",
    )
    parser.add_argument("--base-sha", help="Base SHA override.")
    parser.add_argument("--head-sha", help="Head SHA override.")
    parser.add_argument("--branch-name", help="Branch name override.")
    parser.add_argument("--pr-title", help="Pull request title override.")
    parser.add_argument("--pr-body-file", type=Path, help="Pull request body file.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    pr_body = (
        args.pr_body_file.read_text(encoding="utf-8")
        if args.pr_body_file is not None
        else None
    )
    result = run_check(
        check_spec(args.check_id),
        context=CheckExecutionContext(
            trigger=args.trigger,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
            branch_name=args.branch_name,
            pr_title=args.pr_title,
            pr_body=pr_body,
        ),
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
