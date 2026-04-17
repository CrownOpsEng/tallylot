from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from typing import cast

from repo_support.target_naming import (
    audit_target_naming,
    catalog_path,
    load_target_naming_catalog,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check forward-looking target naming against the repo catalog."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="Run the blocking target-naming check.")
    report = subparsers.add_parser("report", help="Emit a target-naming report.")
    report.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser


def _report_payload() -> dict[str, object]:
    catalog = load_target_naming_catalog()
    findings = tuple(asdict(finding) for finding in audit_target_naming(catalog))
    return {
        "catalog_path": str(catalog_path()),
        "enforced_paths": list(catalog.surfaces.include.paths),
        "findings": findings,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _report_payload()
    findings = cast(list[dict[str, object]], payload["findings"])
    if args.command == "report":
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            if not findings:
                print("target naming report: no findings")
            for item in findings:
                print(f"{item['path']}: [{item['finding_class']}] {item['offending']}")
        return 0

    if not findings:
        print("target naming check passed")
        return 0
    for item in findings:
        replacement = item["replacement"] or "no replacement"
        print(
            f"{item['path']}: [{item['finding_class']}] "
            f"{item['offending']} -> {replacement}"
        )
        print(f"  {item['detail']}")
        if item["exception_rule"] is not None:
            print(f"  exception: {item['exception_rule']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
