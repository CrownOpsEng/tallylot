from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from repo_support.pr_review import PrReviewPlan, changed_paths, classify_changed_paths


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the current PR diff for repo-native review surface coverage."
    )
    parser.add_argument("--base-sha", help="Base commit SHA for the diff range.")
    parser.add_argument("--head-sha", help="Head commit SHA for the diff range.")
    parser.add_argument(
        "--json", action="store_true", help="Emit the audit report as JSON."
    )
    return parser.parse_args(argv)


def _plan_to_json(plan: PrReviewPlan) -> dict[str, object]:
    return {
        "changed_paths": list(plan.changed_paths),
        "grouped_paths": {name: list(paths) for name, paths in plan.grouped_paths},
        "surface_groups": list(plan.surface_groups),
        "review_domains": list(plan.review_domains),
        "targeted_checks": [
            {"name": check.name, "command": list(check.command)}
            for check in plan.targeted_checks
        ],
        "verification_level": plan.verification_level,
        "requires_full_quality_gates": plan.requires_full_quality_gates,
        "requires_ci_parity": plan.requires_ci_parity,
        "requires_pre_merge_packaging_verification": (
            plan.requires_pre_merge_packaging_verification
        ),
        "requires_test_stress_checks": plan.requires_test_stress_checks,
        "requires_coverage_hotspot_report": plan.requires_coverage_hotspot_report,
        "manual_red_team_review_required": bool(plan.changed_paths),
        "unmapped_paths": list(plan.unmapped_paths),
    }


def _emit_text(plan: PrReviewPlan) -> None:
    if not plan.changed_paths:
        print("no changed paths detected")
        return
    print("manual red-team review:", "required")
    print("surface groups:", ", ".join(plan.surface_groups) or "none")
    print("review domains:", ", ".join(plan.review_domains) or "none")
    print("verification level:", plan.verification_level)
    print("full quality gates:", "yes" if plan.requires_full_quality_gates else "no")
    print("ci parity:", "yes" if plan.requires_ci_parity else "no")
    print(
        "pre-merge packaging verification:",
        "yes" if plan.requires_pre_merge_packaging_verification else "no",
    )
    print("stress checks:", "yes" if plan.requires_test_stress_checks else "no")
    print(
        "coverage hotspot report:",
        "yes" if plan.requires_coverage_hotspot_report else "no",
    )
    if plan.targeted_checks:
        print("targeted checks:")
        for check in plan.targeted_checks:
            print(f"  - {check.name}")
    if plan.unmapped_paths:
        print("unmapped paths:")
        for path in plan.unmapped_paths:
            print(f"  - {path}")
    print(
        "review reminder: audit and verification do not replace the mandatory red-team repair loop"
    )


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
    if args.json:
        print(json.dumps(_plan_to_json(plan), indent=2, sort_keys=True))
    else:
        _emit_text(plan)
    if plan.unmapped_paths:
        print(
            "pr review audit failed: changed paths are not mapped to repo review surfaces",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
