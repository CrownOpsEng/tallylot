#!/usr/bin/env python3

"""Profile a raw source folder into deterministic inventory and adapter metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import profile_source_capture


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def profile_source(source: str, raw_dir: Path, out_dir: Path, manifest: Path | None = None) -> dict[str, object]:
    return profile_source_capture(source, raw_dir, out_dir, manifest=manifest)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = profile_source(args.source, args.raw_dir, args.out_dir, manifest=args.manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
