#!/usr/bin/env python3

"""Thin CLI over the shared candidate overlap engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from overlap_engine import (
    build_cointracking_column_map,
    find_header_index,
    find_next_header_index,
    find_trade_table,
    parse_overlap_datetime as parse_datetime,
    summarize_candidate_overlap as summarize_overlap,
    write_candidate_overlap_artifacts as write_overlap_artifacts,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-export-dir", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary, flagged_rows = summarize_overlap(
        baseline_export_dir=args.baseline_export_dir,
        candidate_path=args.candidate,
    )
    if args.out_dir is not None:
        write_overlap_artifacts(args.out_dir, summary, flagged_rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
