#!/usr/bin/env python3

"""Plan or apply canonical routing for a mixed historical intake dump."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import plan_intake_dump


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incoming-dir", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = plan_intake_dump(
        repo_root=args.repo_root,
        incoming_dir=args.incoming_dir,
        report_dir=args.report_dir,
        apply=args.apply,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
