#!/usr/bin/env python3

"""Stage an approved CoinTracking candidate into the import-batch workflow."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Sequence

from overlap_check import summarize_overlap, write_overlap_artifacts
from script_common import CANONICAL_TIMEZONE, COINTRACKING_IMPORT_TIMEZONE, require_file, write_json


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline-export-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--staged-name")
    parser.add_argument("--import-ready-dir", type=Path)
    return parser.parse_args(argv)


def stage_import_batch(
    candidate: Path,
    baseline_export_dir: Path,
    out_dir: Path,
    *,
    staged_name: str | None = None,
    import_ready_dir: Path | None = None,
) -> dict[str, object]:
    candidate = require_file(candidate.resolve(), "CoinTracking candidate")
    out_dir = out_dir.resolve()
    overlap_dir = out_dir / "overlap_check"
    summary, flagged_rows = summarize_overlap(baseline_export_dir, candidate)
    write_overlap_artifacts(overlap_dir, summary, flagged_rows)

    if summary["status"] != "pass":
        result = {
            "status": "blocked",
            "candidate": str(candidate),
            "canonical_timezone": CANONICAL_TIMEZONE,
            "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
            "overlap_summary": str(overlap_dir / "overlap_summary.json"),
            "rows_flagged": summary["rows_flagged"],
            "message": "Candidate failed overlap screening and was not staged.",
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
        "staged_path": str(staged_path),
        "import_ready_path": import_ready_path,
        "overlap_summary": str(overlap_dir / "overlap_summary.json"),
        "rows_flagged": 0,
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
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "staged" else 1


if __name__ == "__main__":
    raise SystemExit(main())
