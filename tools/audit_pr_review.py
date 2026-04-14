from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from repo_support.review_verification import (
    VerificationPlan,
    build_verification_plan,
    changed_paths,
)


def _plan_to_json(plan: VerificationPlan) -> dict[str, object]:
    return {
        "changed_paths": list(plan.surface_report.changed_paths),
        "grouped_paths": {
            name: list(paths) for name, paths in plan.surface_report.grouped_paths
        },
        "surface_groups": list(plan.surface_report.surface_groups),
        "review_domains": list(plan.surface_report.review_domains),
        "mode": plan.mode,
        "trigger": plan.trigger,
        "selected_checks": list(plan.selected_check_ids),
        "blocking_checks": list(plan.blocking_check_ids),
        "nonblocking_checks": list(plan.nonblocking_check_ids),
        "suppressed_checks": [
            {"check_id": check.check_id, "reason": check.reason}
            for check in plan.suppressed_checks
        ],
        "manual_red_team_review_required": bool(plan.surface_report.changed_paths),
        "unmapped_paths": list(plan.surface_report.unmapped_paths),
    }


def _emit_text(plan: VerificationPlan) -> None:
    if not plan.surface_report.changed_paths:
        print("no changed paths detected")
        return
    print("manual red-team review:", "required")
    print("surface groups:", ", ".join(plan.surface_report.surface_groups) or "none")
    print("review domains:", ", ".join(plan.surface_report.review_domains) or "none")
    print("selected verification mode:", plan.mode)
    print("selected checks:", ", ".join(plan.selected_check_ids) or "none")
    if plan.suppressed_checks:
        print("suppressed checks:")
        for check in plan.suppressed_checks:
            print(f"  - {check.check_id}: {check.reason}")
    if plan.surface_report.unmapped_paths:
        print("unmapped paths:")
        for path in plan.surface_report.unmapped_paths:
            print(f"  - {path}")
    print(
        "review reminder: audit and verification do not replace the mandatory "
        "red-team repair loop; use this report to choose the next "
        "issue-finding pass"
    )


def _parse_trigger(value: str) -> str:
    if value not in {"pull_request", "push_main", "local"}:
        raise argparse.ArgumentTypeError(
            "trigger must be pull_request, push_main, or local"
        )
    return value


def _parse_mode(value: str) -> str:
    if value not in {"planned", "full"}:
        raise argparse.ArgumentTypeError("mode must be planned or full")
    return value


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the current PR diff for repo-native review surface coverage."
    )
    parser.add_argument("--base-sha", help="Base commit SHA for the diff range.")
    parser.add_argument("--head-sha", help="Head commit SHA for the diff range.")
    parser.add_argument(
        "--trigger",
        type=_parse_trigger,
        default="local",
        help="Verification trigger to model.",
    )
    parser.add_argument(
        "--mode",
        type=_parse_mode,
        default="planned",
        help="Verification selection mode.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit the audit report as JSON."
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
    if args.json:
        print(json.dumps(_plan_to_json(plan), indent=2, sort_keys=True))
    else:
        _emit_text(plan)
    if plan.surface_report.unmapped_paths:
        print(
            "pr review audit failed: changed paths are not mapped to repo review surfaces",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
