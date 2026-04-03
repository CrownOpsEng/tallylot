#!/usr/bin/env python3

"""Scaffold a new adapter pack fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from script_common import write_json


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--capability", action="append", required=True)
    parser.add_argument("--fixtures-root", type=Path, default=Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "adapter_packs")
    return parser.parse_args(argv)


def scaffold_pack(*, adapter: str, scenario: str, source: str, capabilities: list[str], fixtures_root: Path) -> dict[str, str]:
    root = fixtures_root / adapter / scenario
    raw_dir = root / "raw"
    expected_dir = root / "expected"
    raw_dir.mkdir(parents=True, exist_ok=True)
    expected_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "adapter": adapter,
        "source": source,
        "capabilities": capabilities,
        "expected_adapter": adapter,
        "expected_timezone_status": "passed",
        "expected_normalization_status": "ready",
    }
    write_json(root / "pack.json", manifest)
    for name in ("canonical_events.json", "canonical_balances.json", "exceptions.json", "wallet_evidence.json", "wallet_issues.json"):
        path = expected_dir / name
        if not path.exists():
            write_json(path, [])
    return {
        "pack_root": str(root),
        "pack_json": str(root / "pack.json"),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = scaffold_pack(
        adapter=args.adapter,
        scenario=args.scenario,
        source=args.source,
        capabilities=args.capability,
        fixtures_root=args.fixtures_root,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
