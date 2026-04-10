from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .workflow import validate_workspace_replay


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Replay a reference workspace from raw captures into a clean workspace "
            "and compare semantic parity."
        )
    )
    parser.add_argument("--reference-workspace", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--candidate-workspace")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument(
        "--inspect-archives",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return parser


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return _build_argument_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    reference_workspace = Path(args.reference_workspace).expanduser().resolve()
    report_dir = Path(args.report_dir).expanduser().resolve()
    candidate_workspace = (
        Path(args.candidate_workspace).expanduser().resolve()
        if args.candidate_workspace
        else report_dir / "candidate_workspace"
    )
    selected_sources = frozenset(str(source) for source in args.source)
    report_dir.mkdir(parents=True, exist_ok=True)
    result = validate_workspace_replay(
        reference_workspace=reference_workspace,
        candidate_workspace=candidate_workspace,
        report_dir=report_dir,
        selected_sources=selected_sources,
        inspect_archives=bool(args.inspect_archives),
    )
    print(
        json.dumps(
            {
                "report_dir": str(result.report_dir),
                "candidate_workspace": str(result.candidate_workspace),
                "reference_capture_count": result.reference_capture_count,
                "candidate_capture_count": result.candidate_capture_count,
                "mismatch_count": result.mismatch_count,
                "passed": result.mismatch_count == 0,
            }
        )
    )
    return 0 if result.mismatch_count == 0 else 1
