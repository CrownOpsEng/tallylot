#!/usr/bin/env python3

"""Stage an approved CoinTracking candidate into the import-batch workflow."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Sequence

from overlap_check import summarize_overlap, write_overlap_artifacts
from pipeline_common import REPO_PROJECT_WINDOW_END, parse_canonical_timestamp, repo_project_window_start
from script_common import CANONICAL_TIMEZONE, COINTRACKING_IMPORT_TIMEZONE, read_cointracking_rows, require_file, write_json


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
    candidate = require_file(candidate.resolve(), "CoinTracking candidate")
    out_dir = out_dir.resolve()
    overlap_dir = out_dir / "overlap_check"
    effective_window_start, effective_window_end, normalization_summary_path = resolve_normalization_window(
        candidate=candidate,
        normalization_summary=normalization_summary,
        window_start=window_start,
        window_end=window_end,
    )
    summary, flagged_rows = summarize_overlap(baseline_export_dir, candidate)
    write_overlap_artifacts(overlap_dir, summary, flagged_rows)

    if summary["status"] != "pass":
        result = {
            "status": "blocked",
            "candidate": str(candidate),
            "canonical_timezone": CANONICAL_TIMEZONE,
            "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
            "normalization_summary": normalization_summary_path,
            "normalization_window_start": effective_window_start,
            "normalization_window_end": effective_window_end,
            "overlap_summary": str(overlap_dir / "overlap_summary.json"),
            "rows_flagged": summary["rows_flagged"],
            "rows_outside_normalization_window": 0,
            "message": "Candidate failed overlap screening and was not staged.",
        }
        write_json(out_dir / "stage_summary.json", result)
        return result

    rows_outside_window = count_candidate_rows_outside_window(
        candidate,
        window_start=effective_window_start,
        window_end=effective_window_end,
    )
    if rows_outside_window:
        result = {
            "status": "blocked",
            "candidate": str(candidate),
            "canonical_timezone": CANONICAL_TIMEZONE,
            "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
            "normalization_summary": normalization_summary_path,
            "normalization_window_start": effective_window_start,
            "normalization_window_end": effective_window_end,
            "overlap_summary": str(overlap_dir / "overlap_summary.json"),
            "rows_flagged": 0,
            "rows_outside_normalization_window": rows_outside_window,
            "message": "Candidate contains row(s) outside the approved normalization window and was not staged.",
        }
        write_json(out_dir / "stage_summary.json", result)
        return result

    out_dir.mkdir(parents=True, exist_ok=True)
    staged_path = out_dir / (staged_name or candidate.name)
    shutil.copy2(candidate, staged_path)

    import_ready_path = ""
    if import_ready_dir is not None:
        import_ready_dir = import_ready_dir.resolve()
        import_ready_dir.mkdir(parents=True, exist_ok=True)
        ready_path = import_ready_dir / staged_path.name
        shutil.copy2(staged_path, ready_path)
        import_ready_path = str(ready_path)

    result = {
        "status": "staged",
        "candidate": str(candidate),
        "canonical_timezone": CANONICAL_TIMEZONE,
        "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
        "normalization_summary": normalization_summary_path,
        "normalization_window_start": effective_window_start,
        "normalization_window_end": effective_window_end,
        "staged_path": str(staged_path),
        "import_ready_path": import_ready_path,
        "overlap_summary": str(overlap_dir / "overlap_summary.json"),
        "rows_flagged": 0,
        "rows_outside_normalization_window": 0,
    }
    write_json(out_dir / "stage_summary.json", result)
    return result


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
