from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from repo_support.target_naming import (
    is_target_naming_sensitive_path,
    load_target_naming_catalog,
    run_target_naming_audit,
)
from repo_support.target_naming.reporting import render_human_report, report_payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check forward-looking target naming against the repo policy catalog."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="Run the blocking target-naming check.")
    check.add_argument(
        "--paths",
        nargs="+",
        help="Only audit the supplied paths. Tooling paths expand to a full governed-doc sweep.",
    )
    report = subparsers.add_parser("report", help="Emit a target-naming report.")
    report.add_argument("--json", action="store_true", help="Emit JSON output.")
    report.add_argument(
        "--paths",
        nargs="+",
        help="Only audit the supplied paths. Tooling paths expand to a full governed-doc sweep.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    catalog = load_target_naming_catalog()
    requested_paths: tuple[str, ...] = tuple(args.paths or ())
    report = run_target_naming_audit(paths=requested_paths or None, catalog=catalog)
    if args.command == "report":
        if args.json:
            print(json.dumps(report_payload(report), indent=2, sort_keys=True))
        else:
            print(render_human_report(report))
        return 0

    if requested_paths:
        governed_requested = [
            path
            for path in requested_paths
            if is_target_naming_sensitive_path(path, catalog=catalog)
        ]
        if governed_requested and not report.evaluated_paths:
            print(
                "target naming check failed closed: governed paths were supplied but "
                "no policy evaluation was performed"
            )
            for path in governed_requested:
                print(f"  - {path}")
            return 1
    if report.findings:
        print(render_human_report(report))
        return 1
    print("target naming check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
