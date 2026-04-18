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


def _job_result(job_payload: object) -> str | None:
    if not isinstance(job_payload, Mapping):
        return None
    job_result_payload = cast(Mapping[str, object], job_payload)
    result_object = job_result_payload.get("result")
    return result_object if isinstance(result_object, str) else None


def _planner_failures(needs: Mapping[str, object]) -> tuple[str, ...]:
    failures: list[str] = []
    for planner_check_id in ("plan-pr-review", "plan-main-ci"):
        planner_payload = needs.get(planner_check_id)
        if planner_payload is None:
            continue
        result = _job_result(planner_payload)
        if result == "success":
            continue
        failures.append(f"{planner_check_id}: result={result}")
    return tuple(failures)


def _parse_checks_json(
    raw_value: str,
    *,
    label: str,
    allow_blank: bool,
) -> tuple[str, ...]:
    if not raw_value.strip():
        if allow_blank:
            return ()
        raise ValueError(f"{label}: missing workflow output")
    try:
        payload_object: object = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label}: invalid workflow output") from exc
    if not isinstance(payload_object, list):
        raise ValueError(f"{label}: expected JSON array of strings")
    payload_items = cast(list[object], payload_object)
    payload: list[str] = []
    for item in payload_items:
        if not isinstance(item, str):
            raise ValueError(f"{label}: expected JSON array of strings")
        payload.append(item)
    return tuple(payload)


def _collect_check_failures(
    *,
    selected_checks: Sequence[str],
    nonblocking_checks: set[str],
    needs: Mapping[str, object],
) -> tuple[list[str], list[str]]:
    blocking_failures: list[str] = []
    blocked_checks: list[str] = []
    for check_id in selected_checks:
        if check_id in {"plan-pr-review", "plan-main-ci"}:
            continue
        result = _job_result(needs.get(check_id))
        if result is None:
            if check_id in nonblocking_checks:
                print(
                    f"[non-blocking] {check_id} result=not-run-in-aggregate",
                    flush=True,
                )
                continue
            blocking_failures.append(f"{check_id}: missing job result")
            continue
        if result == "success":
            continue
        if check_id in nonblocking_checks:
            print(f"[non-blocking] {check_id} result={result}", flush=True)
            continue
        if result == "skipped":
            blocked_checks.append(check_id)
            continue
        blocking_failures.append(f"{check_id}: result={result}")
    return blocking_failures, blocked_checks


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    needs = _job_results(args.needs_json)
    planner_failures = list(_planner_failures(needs))
    allow_blank_outputs = bool(planner_failures)

    try:
        selected_checks = _parse_checks_json(
            args.selected_checks_json,
            label="selected checks",
            allow_blank=allow_blank_outputs,
        )
        nonblocking_checks = set(
            _parse_checks_json(
                args.nonblocking_checks_json,
                label="non-blocking checks",
                allow_blank=allow_blank_outputs,
            )
        )
    except ValueError as exc:
        planner_failures.append(str(exc))
        print("review verification failed:", file=sys.stderr)
        for failure in planner_failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    blocking_failures, blocked_checks = _collect_check_failures(
        selected_checks=selected_checks,
        nonblocking_checks=nonblocking_checks,
        needs=needs,
    )
    blocking_failures = planner_failures + blocking_failures

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
