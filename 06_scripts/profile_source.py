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
from wallet_inventory import detect_repo_root, profile_wallet_identifiers, refresh_wallet_inventory


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
    wallet_inventory, wallet_issues, wallet_summary = profile_wallet_identifiers(source, raw_dir)
    profile = replace(
        profile,
        timezone_summary=timezone_summary,
        timezone_issues=timezone_issues,
        wallet_inventory=wallet_inventory,
        wallet_issues=wallet_issues,
        wallet_summary=wallet_summary,
    )
    profile_json, inventory_csv = write_profile_artifacts(out_dir, profile)
    summary = {
        "source": profile.source,
        "adapter": profile.adapter,
        "adapter_supported": profile.adapter_supported,
        "manifest_fingerprint": profile.manifest_fingerprint,
        "timezone_status": timezone_summary["status"],
        "timezone_issue_count": timezone_summary["issue_count"],
        "wallet_status": wallet_summary["status"],
        "wallet_count": wallet_summary["wallet_count"],
        "wallet_issue_count": wallet_summary["issue_count"],
        "profile_json": str(profile_json),
        "profile_inventory_csv": str(inventory_csv),
        "files_profiled": len(profile.file_inventory),
    }
    repo_root = detect_repo_root(raw_dir)
    if repo_root is not None and repo_root in out_dir.resolve().parents:
        repo_wallet_summary = refresh_wallet_inventory(repo_root)
        summary["wallet_inventory_csv"] = str(repo_root / "03_analysis" / "inventory" / "wallet_inventory.csv")
        summary["wallet_inventory_status"] = repo_wallet_summary["status"]
        summary["wallet_inventory_issue_count"] = repo_wallet_summary["issue_count"]
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = profile_source(args.source, args.raw_dir, args.out_dir, manifest=args.manifest)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
