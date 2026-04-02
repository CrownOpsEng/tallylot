#!/usr/bin/env python3

"""Normalize a raw source folder into canonical events, balances, and exceptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import normalize_source_capture


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--profile-json", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--exception-decisions", type=Path)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def normalize_source(
    source: str,
    raw_dir: Path,
    out_dir: Path,
    *,
    profile_json: Path | None = None,
    manifest: Path | None = None,
    exception_decisions: Path | None = None,
    window_start: str | None = None,
    window_end: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    return normalize_source_capture(
        source,
        raw_dir,
        out_dir,
        profile_json=profile_json,
        manifest=manifest,
        exception_decisions=exception_decisions,
        window_start=window_start,
        window_end=window_end,
        force=force,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = normalize_source(
        args.source,
        args.raw_dir,
        args.out_dir,
        profile_json=args.profile_json,
        manifest=args.manifest,
        exception_decisions=args.exception_decisions,
        window_start=args.window_start,
        window_end=args.window_end,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
