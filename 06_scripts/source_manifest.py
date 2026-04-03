#!/usr/bin/env python3

"""Build a deterministic file manifest for a source capture folder."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from script_common import require_directory, sha256sum, write_csv_rows


IGNORED_NAMES = {"README.md", ".gitkeep"}


def validate_source_dir(source_dir: Path) -> Path:
    return require_directory(source_dir.resolve(), "Source directory")

def build_manifest_rows(
    source_dir: Path,
    output: Path,
) -> list[dict[str, object]]:
    source_dir = validate_source_dir(source_dir)
    output = output.resolve()
    rows = []
    for path in sorted(
        p
        for p in source_dir.rglob("*")
        if p.is_file() and p.resolve() != output and p.name not in IGNORED_NAMES
    ):
        rows.append(
            {
                "filename": str(path.relative_to(source_dir)),
                "bundle_id": "",
                "bundle_type": "",
                "bundle_relative_path": str(path.relative_to(source_dir)),
                "source_paths": "",
                "alias_group": "",
                "collision_status": "",
                "size_bytes": path.stat().st_size,
                "sha256": sha256sum(path),
            }
        )
    return rows


def write_manifest(output: Path, rows: list[dict[str, object]]) -> None:
    write_csv_rows(
        output,
        ["filename", "bundle_id", "bundle_type", "bundle_relative_path", "source_paths", "alias_group", "collision_status", "size_bytes", "sha256"],
        rows,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output.resolve()
    rows = build_manifest_rows(
        args.source_dir,
        output,
    )
    write_manifest(output, rows)
    print(f"Wrote manifest with {len(rows)} file(s) to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
