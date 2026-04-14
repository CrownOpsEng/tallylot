from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from typing import cast


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate selected workflow job results for review verification."
    )
    parser.add_argument(
        "--selected-checks-json",
        required=True,
        help="JSON array of selected atomic checks.",
    )
    parser.add_argument(
        "--nonblocking-checks-json",
        required=True,
        help="JSON array of selected non-blocking atomic checks.",
    )
    parser.add_argument(
        "--needs-json",
        required=True,
        help="Serialized GitHub Actions needs context.",
    )
    return parser.parse_args(argv)


def _job_results(needs_json: str) -> Mapping[str, object]:
    return cast(Mapping[str, object], json.loads(needs_json))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    selected_checks = tuple(cast(list[str], json.loads(args.selected_checks_json)))
    nonblocking_checks = set(cast(list[str], json.loads(args.nonblocking_checks_json)))
    needs = _job_results(args.needs_json)

    blocking_failures: list[str] = []
    blocked_checks: list[str] = []

    for check_id in selected_checks:
        if check_id in {"plan-pr-review", "plan-main-ci"}:
            continue
        job_payload = needs.get(check_id)
        if not isinstance(job_payload, Mapping):
            if check_id in nonblocking_checks:
                print(
                    f"[non-blocking] {check_id} result=not-run-in-aggregate",
                    flush=True,
                )
                continue
            blocking_failures.append(f"{check_id}: missing job result")
            continue
        job_result_payload = cast(Mapping[str, object], job_payload)
        result_object = job_result_payload.get("result")
        result = result_object if isinstance(result_object, str) else None
        if result == "success":
            continue
        if check_id in nonblocking_checks:
            print(f"[non-blocking] {check_id} result={result}", flush=True)
            continue
        if result == "skipped":
            blocked_checks.append(check_id)
        else:
            blocking_failures.append(f"{check_id}: result={result}")

    if blocked_checks:
        print(
            "blocking checks were skipped because an upstream dependency failed: "
            + ", ".join(blocked_checks),
            file=sys.stderr,
        )
    if blocking_failures:
        print("review verification failed:", file=sys.stderr)
        for failure in blocking_failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    if blocked_checks:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
