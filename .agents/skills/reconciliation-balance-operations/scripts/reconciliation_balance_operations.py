from __future__ import annotations

import argparse
from importlib import import_module
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()


def _repo_root() -> Path:
    for candidate in SCRIPT_PATH.parents:
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "repo_support"
        ).is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return candidate
    raise RuntimeError("Could not locate repo root for reconciliation balance skill")


if (
    sys.version_info < (3, 12)
    and os.environ.get("TALLYLOT_BALANCE_OPERATIONS_BOOTSTRAPPED") != "1"
):
    os.environ.setdefault(
        "UV_PROJECT_ENVIRONMENT",
        str(Path.home() / ".venvs" / "tallylot-py312"),
    )
    os.environ["TALLYLOT_BALANCE_OPERATIONS_BOOTSTRAPPED"] = "1"
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

_reconciliation = import_module("tallylot.application.reconciliation")
BalanceCheckRequest = _reconciliation.BalanceCheckRequest
BalanceCoverageRequest = _reconciliation.BalanceCoverageRequest
BalanceSummaryRequest = _reconciliation.BalanceSummaryRequest
to_resource_ref = import_module("tallylot.application.resource_refs").to_resource_ref
_runtime = import_module("tallylot.infrastructure.composition.runtime")
balance_check_workflow = _runtime.balance_check_workflow
balance_coverage_workflow = _runtime.balance_coverage_workflow
balance_summary_workflow = _runtime.balance_summary_workflow


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run balance reconciliation operations through runtime workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--input-root", type=Path, required=True)
    inspect_parser.add_argument("--output", type=Path, required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--input-root", type=Path, required=True)
    check_parser.add_argument("--output-root", type=Path, required=True)
    check_parser.add_argument("--source", action="append", default=[])

    summarize_parser = subparsers.add_parser("summarize")
    summarize_parser.add_argument("--coverage", type=Path, required=True)
    summarize_parser.add_argument("--check-summary", type=Path, required=True)
    summarize_parser.add_argument("--output", type=Path, required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--input-root", type=Path, required=True)
    run_parser.add_argument("--analysis-root", type=Path, required=True)
    run_parser.add_argument("--source", action="append", default=[])

    args = parser.parse_args(argv)
    if args.command == "inspect":
        payload = balance_coverage_workflow().execute(
            BalanceCoverageRequest(
                input_root_ref=to_resource_ref(args.input_root),
                coverage_output_ref=to_resource_ref(args.output),
            )
        )
        print(json.dumps(payload.__dict__, default=str))
        return 0
    if args.command == "check":
        payload = balance_check_workflow().execute(
            BalanceCheckRequest(
                input_root_ref=to_resource_ref(args.input_root),
                output_root_ref=to_resource_ref(args.output_root),
                sources=tuple(args.source),
            )
        )
        print(json.dumps(payload.__dict__, default=str))
        return 0
    if args.command == "summarize":
        payload = balance_summary_workflow().execute(
            BalanceSummaryRequest(
                coverage_input_ref=to_resource_ref(args.coverage),
                check_summary_input_ref=to_resource_ref(args.check_summary),
                summary_output_ref=to_resource_ref(args.output),
            )
        )
        print(json.dumps(payload.__dict__, default=str))
        return 0
    coverage_output = args.analysis_root / "balance_coverage.csv"
    check_output_root = args.analysis_root / "checks"
    summary_output = args.analysis_root / "balance_reconciliation_summary.json"
    coverage_response = balance_coverage_workflow().execute(
        BalanceCoverageRequest(
            input_root_ref=to_resource_ref(args.input_root),
            coverage_output_ref=to_resource_ref(coverage_output),
        )
    )
    check_response = balance_check_workflow().execute(
        BalanceCheckRequest(
            input_root_ref=to_resource_ref(args.input_root),
            output_root_ref=to_resource_ref(check_output_root),
            sources=tuple(args.source),
        )
    )
    summary_response = balance_summary_workflow().execute(
        BalanceSummaryRequest(
            coverage_input_ref=coverage_response.coverage_output_ref,
            check_summary_input_ref=check_response.check_summary_output_ref,
            summary_output_ref=to_resource_ref(summary_output),
        )
    )
    print(
        json.dumps(
            {
                "coverage_output_ref": coverage_response.coverage_output_ref,
                "check_summary_output_ref": check_response.check_summary_output_ref,
                "summary_output_ref": summary_response.summary_output_ref,
                "blocker_output_ref": summary_response.blocker_output_ref,
                "latest_portfolio_clean_date": summary_response.latest_portfolio_clean_date,
                "latest_portfolio_source_backed_date": summary_response.latest_portfolio_source_backed_date,
                "latest_clean_source_date": summary_response.latest_clean_source_date,
                "latest_source_backed_date": summary_response.latest_source_backed_date,
                "latest_observed_assertion_date": summary_response.latest_observed_assertion_date,
            },
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
