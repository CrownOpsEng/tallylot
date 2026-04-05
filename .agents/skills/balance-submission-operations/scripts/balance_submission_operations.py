from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tallylot.application.checkpoints.balance_submission.contracts import (
        BalanceSubmissionValidationResult,
    )

SCRIPT_PATH = Path(__file__).resolve()


def _repo_root() -> Path:
    for candidate in SCRIPT_PATH.parents:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "repo_support"
        ).is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            from repo_support.paths import repo_root

            return repo_root()
    raise RuntimeError("Could not locate repo root for balance submission skill")


if (
    sys.version_info < (3, 12)
    and os.environ.get("TALLYLOT_BALANCE_SUBMISSION_BOOTSTRAPPED") != "1"
):
    os.environ.setdefault(
        "UV_PROJECT_ENVIRONMENT",
        str(Path.home() / ".venvs" / "tallylot-py312"),
    )
    os.environ["TALLYLOT_BALANCE_SUBMISSION_BOOTSTRAPPED"] = "1"
    os.execvp(
        "uv",
        [
            "uv",
            "run",
            "python",
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
    )

REPO_ROOT = _repo_root()
SRC_ROOT = REPO_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _default_submission_root(source: str) -> Path:
    from tallylot.infrastructure.composition.runtime import configured_workspace_root

    return (
        configured_workspace_root()
        / "working"
        / "supporting_artifacts"
        / "balance_submissions"
        / source
    )


def _default_output_root(source: str) -> Path:
    from tallylot.infrastructure.composition.runtime import configured_workspace_root

    return configured_workspace_root() / "working" / "normalized" / source


def main(argv: Sequence[str] | None = None) -> int:
    from tallylot.application.checkpoints.balance_submission.schema import (
        BALANCE_CONFIRMATIONS_FILENAME,
        BALANCES_FILENAME,
        ISSUES_FILENAME,
        LOCATION_INVENTORY_FILENAME,
        SUMMARY_FILENAME,
    )
    from tallylot.application.checkpoints.contracts import (
        ScaffoldBalanceSubmissionRequest,
        SubmitBalancesRequest,
    )
    from tallylot.application.resource_refs import to_resource_ref
    from tallylot.infrastructure.composition.runtime import (
        scaffold_balance_submission_use_case,
        submit_balances_use_case,
    )
    from tallylot.application.checkpoints.balance_submission.validation import (
        validate_balance_submission,
    )

    parser = argparse.ArgumentParser(
        description="Run manual balance submission operations through runtime workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold")
    scaffold_parser.add_argument("--source", required=True)
    scaffold_parser.add_argument("--submission-root", type=Path)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--source", required=True)
    inspect_parser.add_argument("--submission-root", type=Path)

    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--source", required=True)
    submit_parser.add_argument("--submission-root", type=Path)
    submit_parser.add_argument("--output-root", type=Path)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--source", required=True)
    run_parser.add_argument("--submission-root", type=Path)
    run_parser.add_argument("--output-root", type=Path)

    args = parser.parse_args(argv)
    submission_root = args.submission_root or _default_submission_root(args.source)

    if args.command == "scaffold":
        scaffold_payload = scaffold_balance_submission_use_case().execute(
            ScaffoldBalanceSubmissionRequest(
                source=args.source,
                submission_root_ref=to_resource_ref(submission_root),
            )
        )
        print(json.dumps(scaffold_payload.__dict__, default=str))
        return 0

    if args.command == "inspect":
        inspection_payload = _inspection_payload(
            validate_balance_submission(
                submission_root,
                expected_source=args.source,
            ),
            submission_root=submission_root,
            balances_path=submission_root / BALANCES_FILENAME,
            balance_confirmations_path=submission_root / BALANCE_CONFIRMATIONS_FILENAME,
            location_inventory_path=submission_root / LOCATION_INVENTORY_FILENAME,
        )
        print(json.dumps(inspection_payload, default=str))
        return 0

    output_root = args.output_root or _default_output_root(args.source)
    if args.command == "submit":
        submit_payload = submit_balances_use_case().execute(
            SubmitBalancesRequest(
                source=args.source,
                submission_root_ref=to_resource_ref(submission_root),
                output_root_ref=to_resource_ref(output_root),
            )
        )
        print(
            json.dumps(
                {
                    **submit_payload.__dict__,
                    "issues_path": str(output_root / ISSUES_FILENAME),
                    "summary_path": str(output_root / SUMMARY_FILENAME),
                },
                default=str,
            )
        )
        return 0

    scaffold_balance_submission_use_case().execute(
        ScaffoldBalanceSubmissionRequest(
            source=args.source,
            submission_root_ref=to_resource_ref(submission_root),
        )
    )
    inspection_payload = _inspection_payload(
        validate_balance_submission(
            submission_root,
            expected_source=args.source,
        ),
        submission_root=submission_root,
        balances_path=submission_root / BALANCES_FILENAME,
        balance_confirmations_path=submission_root / BALANCE_CONFIRMATIONS_FILENAME,
        location_inventory_path=submission_root / LOCATION_INVENTORY_FILENAME,
    )
    if inspection_payload["ready_for_submit"] is False:
        print(
            json.dumps(
                {
                    **inspection_payload,
                    "blocked": True,
                    "stage": "inspect",
                },
                default=str,
            )
        )
        return 0
    submit_payload = submit_balances_use_case().execute(
        SubmitBalancesRequest(
            source=args.source,
            submission_root_ref=to_resource_ref(submission_root),
            output_root_ref=to_resource_ref(output_root),
        )
    )
    print(
        json.dumps(
            {
                **submit_payload.__dict__,
                "issues_path": str(output_root / ISSUES_FILENAME),
                "summary_path": str(output_root / SUMMARY_FILENAME),
            },
            default=str,
        )
    )
    return 0


def _inspection_payload(
    validation: "BalanceSubmissionValidationResult",
    *,
    submission_root: Path,
    balances_path: Path,
    balance_confirmations_path: Path,
    location_inventory_path: Path,
) -> dict[str, object]:
    from tallylot.application.checkpoints.balance_submission.schema import (
        BALANCE_CONFIRMATIONS_FILENAME,
        BALANCES_FILENAME,
        LOCATION_INVENTORY_FILENAME,
    )

    issues = [issue.to_row() for issue in validation.issues]
    return {
        "submission_root": str(submission_root),
        "required_files_present": {
            BALANCES_FILENAME: balances_path.is_file(),
            BALANCE_CONFIRMATIONS_FILENAME: balance_confirmations_path.is_file(),
        },
        "optional_files_present": {
            LOCATION_INVENTORY_FILENAME: location_inventory_path.is_file(),
        },
        "balance_row_count": len(validation.balance_rows),
        "balance_confirmation_row_count": len(validation.balance_confirmation_rows),
        "location_inventory_row_count": len(validation.location_inventory_rows),
        "issue_count": len(validation.issues),
        "ready_for_submit": len(validation.issues) == 0,
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(main())
