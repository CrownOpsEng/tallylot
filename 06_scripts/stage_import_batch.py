#!/usr/bin/env python3

"""Stage an approved CoinTracking candidate into the import-batch workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import (
    count_candidate_rows_outside_window,
    read_normalization_summary,
    resolve_normalization_window,
    stage_import_candidate,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline-export-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--staged-name")
    parser.add_argument("--import-ready-dir", type=Path)
    parser.add_argument("--normalization-summary", type=Path)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    return parser.parse_args(argv)


def count_candidate_rows_outside_window(candidate: Path, *, window_start: str, window_end: str) -> int:
    start_dt = parse_canonical_timestamp(window_start, label="window_start") if window_start else None
    end_dt = parse_canonical_timestamp(window_end, label="window_end") if window_end else None
    rows_outside_window = 0
    for row in read_cointracking_rows(candidate):
        date_text = (row.get("Date") or "").strip()
        date_dt = parse_canonical_timestamp(date_text, label="candidate Date")
        if start_dt is not None and date_dt < start_dt:
            rows_outside_window += 1
            continue
        if end_dt is not None and date_dt > end_dt:
            rows_outside_window += 1
    return rows_outside_window


def read_normalization_summary(path: Path) -> dict[str, object]:
    summary_path = require_file(path.resolve(), "Normalization summary")
    with summary_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Normalization summary must be a JSON object: {summary_path}")
    return payload


def resolve_normalization_window(
    *,
    candidate: Path,
    normalization_summary: Path | None,
    window_start: str | None,
    window_end: str | None,
) -> tuple[str, str, str]:
    effective_window_start = repo_project_window_start() if window_start is None else window_start
    effective_window_end = REPO_PROJECT_WINDOW_END if window_end is None else window_end
    summary_path = normalization_summary
    if summary_path is None:
        sibling_path = candidate.parent / "normalization_summary.json"
        if sibling_path.exists():
            summary_path = sibling_path

    if summary_path is not None:
        payload = read_normalization_summary(summary_path)
        if window_start is None:
            summary_start = payload.get("normalization_window_start", "")
            if isinstance(summary_start, str) and summary_start:
                effective_window_start = summary_start
        if window_end is None:
            summary_end = payload.get("normalization_window_end", "")
            if isinstance(summary_end, str) and summary_end:
                effective_window_end = summary_end
        return effective_window_start, effective_window_end, str(summary_path.resolve())

    return effective_window_start, effective_window_end, ""


def stage_import_batch(
    candidate: Path,
    baseline_export_dir: Path,
    out_dir: Path,
    *,
    staged_name: str | None = None,
    import_ready_dir: Path | None = None,
    normalization_summary: Path | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
) -> dict[str, object]:
    return stage_import_candidate(
        candidate,
        baseline_export_dir,
        out_dir,
        staged_name=staged_name,
        import_ready_dir=import_ready_dir,
        normalization_summary=normalization_summary,
        window_start=window_start,
        window_end=window_end,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = stage_import_batch(
        args.candidate,
        args.baseline_export_dir,
        args.out_dir,
        staged_name=args.staged_name,
        import_ready_dir=args.import_ready_dir,
        normalization_summary=args.normalization_summary,
        window_start=args.window_start,
        window_end=args.window_end,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "staged" else 1


if __name__ == "__main__":
    raise SystemExit(main())
