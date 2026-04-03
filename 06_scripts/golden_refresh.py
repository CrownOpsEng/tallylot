#!/usr/bin/env python3

"""Refresh adapter pack golden outputs from current pipeline behavior."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline import normalize_source_capture, profile_wallet_identifiers
from script_common import write_json
from tests.support.adapter_packs import load_adapter_packs, stage_adapter_pack


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path(".tmp_golden_refresh"))
    return parser.parse_args(argv)


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def strip_dynamic_paths(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {key: value for key, value in row.items() if key not in {"capture_path", "evidence_path"}}
        for row in rows
    ]


def _stage_pack_root(pack_root: Path, temp_root: Path) -> Path:
    known_pack = next((candidate for candidate in load_adapter_packs() if candidate.root == pack_root), None)
    if known_pack is not None:
        return stage_adapter_pack(known_pack, temp_root)

    payload = json.loads((pack_root / "pack.json").read_text(encoding="utf-8"))
    capture_dir_name = str(payload.get("capture_dir_name", "")) or pack_root.name
    target = temp_root / capture_dir_name / "raw"
    shutil.copytree(pack_root / "raw", target)
    return target


def refresh_pack(pack_root: Path, workspace: Path) -> dict[str, object]:
    payload = json.loads((pack_root / "pack.json").read_text(encoding="utf-8"))
    source = str(payload["source"])
    capabilities = set(payload.get("capabilities", []))
    expected_dir = pack_root / "expected"
    temp_root = workspace / pack_root.parent.name / pack_root.name
    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)
    staged_raw = _stage_pack_root(pack_root, temp_root)

    written: dict[str, object] = {"pack": str(pack_root), "written": []}
    if "normalize" in capabilities:
        out_dir = temp_root / "normalized"
        normalize_source_capture(source, staged_raw, out_dir, force=True)
        for name, path in (
            ("canonical_events.json", out_dir / "canonical_events.csv"),
            ("canonical_balances.json", out_dir / "canonical_balances.csv"),
            ("exceptions.json", out_dir / "exceptions.csv"),
        ):
            write_json(expected_dir / name, read_csv_dicts(path))
            written["written"].append(str(expected_dir / name))

    if "wallet" in capabilities:
        evidence, issues, _ = profile_wallet_identifiers(source, staged_raw, adapter_name=str(payload.get("expected_adapter", "")))
        write_json(expected_dir / "wallet_evidence.json", strip_dynamic_paths(evidence))
        write_json(expected_dir / "wallet_issues.json", strip_dynamic_paths(issues))
        written["written"].extend(
            [
                str(expected_dir / "wallet_evidence.json"),
                str(expected_dir / "wallet_issues.json"),
            ]
        )

    return written


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = refresh_pack(args.pack.resolve(), args.workspace.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
