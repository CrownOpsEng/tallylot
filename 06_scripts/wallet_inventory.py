#!/usr/bin/env python3

"""Build a canonical wallet inventory from profiled source captures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pipeline import build_wallet_inventory_repo, profile_wallet_identifiers, refresh_wallet_inventory


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def detect_repo_root(start: Path) -> Path | None:
    candidate = start.resolve()
    if candidate.is_file():
        candidate = candidate.parent
    for path in (candidate, *candidate.parents):
        if (path / "03_analysis" / "issues" / "source_inventory.csv").exists():
            return path
    return None


def build_wallet_inventory(repo_root: Path):
    return build_wallet_inventory_repo(repo_root)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = detect_repo_root(args.repo_root) or args.repo_root.resolve()
    summary = refresh_wallet_inventory(repo_root, out_dir=args.out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
