#!/usr/bin/env python3

"""Profile a raw source folder into deterministic inventory and adapter metadata."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Sequence

from pipeline_common import build_source_profile, write_profile_artifacts
from source_adapters import get_adapter


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def profile_source(source: str, raw_dir: Path, out_dir: Path, manifest: Path | None = None) -> dict[str, object]:
    adapter = get_adapter(source)
    profile = build_source_profile(
        source=source,
        raw_dir=raw_dir,
        manifest_path=manifest,
        adapter_name=adapter.name,
        adapter_supported=adapter.supported,
    )
    timezone_summary, timezone_issues = adapter.validate_profile_timezones(profile)
    profile = replace(profile, timezone_summary=timezone_summary, timezone_issues=timezone_issues)
    profile_json, inventory_csv = write_profile_artifacts(out_dir, profile)
    return {
        "source": profile.source,
        "adapter": profile.adapter,
        "adapter_supported": profile.adapter_supported,
        "manifest_fingerprint": profile.manifest_fingerprint,
        "timezone_status": timezone_summary["status"],
        "timezone_issue_count": timezone_summary["issue_count"],
        "profile_json": str(profile_json),
        "profile_inventory_csv": str(inventory_csv),
        "files_profiled": len(profile.file_inventory),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = profile_source(args.source, args.raw_dir, args.out_dir, manifest=args.manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
