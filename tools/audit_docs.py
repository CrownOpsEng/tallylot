from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from repo_support.docs_audit import run_docs_audit
from repo_support.docs_audit.reporting import render_human_report, report_payload
from repo_support.docs_audit.surfaces import is_docs_audit_substrate_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit live repo document semantics and cross-surface parity."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Run the blocking docs-audit check.")
    check.add_argument(
        "--paths",
        nargs="+",
        help="Optional changed paths. Any docs-audit substrate path expands to a full-repo audit.",
    )

    report = subparsers.add_parser("report", help="Emit a docs-audit report.")
    report.add_argument("--json", action="store_true", help="Emit JSON output.")
    report.add_argument(
        "--paths",
        nargs="+",
        help="Optional changed paths. Any docs-audit substrate path expands to a full-repo audit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    requested_paths: tuple[str, ...] = tuple(args.paths or ())
    report = run_docs_audit(paths=requested_paths or None)

    if args.command == "report":
        if args.json:
            print(json.dumps(report_payload(report), indent=2, sort_keys=True))
        else:
            print(render_human_report(report))
        return 0

    governed_requested = [
        path for path in requested_paths if is_docs_audit_substrate_path(path)
    ]
    if governed_requested and not report.evaluated_rule_ids:
        print(
            "docs audit check failed closed: governed paths were supplied but no audit rule was evaluated"
        )
        for path in governed_requested:
            print(f"  - {path}")
        return 1

    if report.findings:
        print(render_human_report(report))
        return 1

    print("docs audit check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
