from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from repo_support.paths import adapter_packs_root
from repo_support.capture_roots import materialize_capture_root
from tallylot.application.normalization import NormalizeRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.infrastructure.composition import (
    build_profile_use_case,
    normalize_source_use_case,
)
from tallylot.infrastructure.discovery.adapters import build_registry
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tools.adapter_packs import AdapterPack, select_adapter_packs

_EXPECTED_NORMALIZATION_ARTIFACTS = (
    "facts",
    "fact_annotations",
    "location_annotations",
    "balances",
    "balance_evidence",
    "exceptions",
    "normalization_reviews",
    "normalization_summary",
)
_EXPECTED_LOCATION_ARTIFACTS = (
    "location_inventory",
    "wallet_issues",
)
_EXPECTED_ARTIFACTS = _EXPECTED_NORMALIZATION_ARTIFACTS + _EXPECTED_LOCATION_ARTIFACTS


def _sanitize_public_fixture_payload(
    payload: object,
    *,
    raw_paths: tuple[Path, ...],
) -> object:
    raw_path_texts = tuple(str(path) for path in raw_paths)

    if isinstance(payload, dict):
        payload_dict = cast(dict[object, object], payload)
        return {
            key: _sanitize_public_fixture_payload(value, raw_paths=raw_paths)
            for key, value in payload_dict.items()
        }
    if isinstance(payload, list):
        payload_list = cast(list[object], payload)
        return [
            _sanitize_public_fixture_payload(item, raw_paths=raw_paths)
            for item in payload_list
        ]
    if isinstance(payload, str):
        for raw_path_text in raw_path_texts:
            if payload == raw_path_text:
                return "<fixture-raw-dir>"
            if payload.startswith(raw_path_text + "/"):
                return payload.replace(raw_path_text, "<fixture-raw-dir>", 1)
    return payload


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh adapter-pack golden outputs through the typed services.",
    )
    parser.add_argument(
        "--pack-root",
        type=Path,
        default=None,
        help="Root containing adapter pack fixtures.",
    )
    parser.add_argument(
        "--pack",
        action="append",
        dest="packs",
        default=[],
        help="Specific adapter pack id to refresh, for example 'structured_csv/basic'.",
    )
    parser.add_argument(
        "--capability",
        default=None,
        help="Filter packs by capability such as 'normalize' or 'location_inventory'.",
    )
    return parser


def _collect_pack_outputs(pack: AdapterPack) -> dict[str, object]:
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    profile_use_case = build_profile_use_case()
    normalization_use_case = normalize_source_use_case()
    with TemporaryDirectory(prefix="tallylot-pack-refresh-") as temp_dir_name:
        raw_capture_root = materialize_capture_root(
            Path(temp_dir_name),
            source=pack.source,
            source_dir=pack.raw_dir,
            capture_label=pack.capture_dir_name or "2026-03-23T14-15-16Z",
        )
        profile = profile_use_case.create_profile(pack.source, raw_capture_root)
        adapter = registry.source_adapter(str(profile.adapter_id))
        location_inventory, wallet_issues = adapter.extract_location_inventory(
            pack.source,
            raw_capture_root,
            profile,
        )
        payloads: dict[str, object] = {
            "location_inventory": [record.to_row() for record in location_inventory],
            "wallet_issues": [issue.to_row() for issue in wallet_issues],
        }
        if pack.supports("normalize"):
            output_dir = Path(temp_dir_name) / "normalized"
            normalization_use_case.execute(
                NormalizeRequest(
                    source=pack.source,
                    raw_capture_ref=to_resource_ref(raw_capture_root),
                    normalized_output_ref=to_resource_ref(output_dir),
                )
            )
            payloads.update(
                {
                    "facts": artifacts.read_rows(output_dir / "facts.csv"),
                    "fact_annotations": json.loads(
                        (output_dir / "fact_annotations.json").read_text(
                            encoding="utf-8"
                        )
                    ),
                    "location_annotations": json.loads(
                        (output_dir / "location_annotations.json").read_text(
                            encoding="utf-8"
                        )
                    ),
                    "balances": artifacts.read_rows(output_dir / "balances.csv"),
                    "balance_evidence": artifacts.read_rows(
                        output_dir / "balance_evidence.csv"
                    ),
                    "exceptions": artifacts.read_rows(output_dir / "exceptions.csv"),
                    "normalization_reviews": artifacts.read_rows(
                        output_dir / "normalization_reviews.csv"
                    ),
                    "normalization_summary": json.loads(
                        (output_dir / "normalization_summary.json").read_text(
                            encoding="utf-8"
                        )
                    ),
                }
            )
        return {
            artifact_name: _sanitize_public_fixture_payload(
                payload,
                raw_paths=(pack.raw_dir, raw_capture_root),
            )
            for artifact_name, payload in payloads.items()
        }


def _refresh_pack(pack: AdapterPack) -> tuple[Path, ...]:
    payloads = _collect_pack_outputs(pack)
    pack.expected_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    artifact_names: tuple[str, ...] = _EXPECTED_LOCATION_ARTIFACTS
    if pack.supports("normalize"):
        artifact_names = (
            _EXPECTED_NORMALIZATION_ARTIFACTS + _EXPECTED_LOCATION_ARTIFACTS
        )
    for artifact_name in artifact_names:
        target = pack.expected_dir / f"{artifact_name}.json"
        target.write_text(
            json.dumps(payloads[artifact_name], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written_paths.append(target)
    return tuple(written_paths)


def main(argv: list[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    pack_root = (
        adapter_packs_root() if args.pack_root is None else args.pack_root.resolve()
    )
    packs = select_adapter_packs(
        pack_root=pack_root,
        selected_ids=tuple(args.packs),
        capability=args.capability,
    )
    if not packs:
        print("No adapter packs matched the requested filters.")
        return 0
    for pack in packs:
        print(f"Refreshing {pack.id}")
        for path in _refresh_pack(pack):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
