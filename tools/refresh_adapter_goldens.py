from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from tallylot.application.normalization import NormalizeRequest
from tallylot.infrastructure.composition import build_profile_use_case, normalize_source_use_case
from tallylot.infrastructure.discovery.adapters import build_registry
from tallylot.infrastructure.serialization import FilesystemArtifactStore
from tools.adapter_packs import DEFAULT_PACK_ROOT, AdapterPack, select_adapter_packs

EXPECTED_NORMALIZATION_ARTIFACTS = (
    "facts",
    "fact_annotations",
    "location_annotations",
    "balances",
    "balance_evidence",
    "exceptions",
    "normalization_reviews",
    "normalization_summary",
)
EXPECTED_LOCATION_ARTIFACTS = (
    "location_inventory",
    "wallet_issues",
)
EXPECTED_ARTIFACTS = EXPECTED_NORMALIZATION_ARTIFACTS + EXPECTED_LOCATION_ARTIFACTS


def _sanitize_public_fixture_payload(payload: object, *, raw_dir: Path) -> object:
    raw_dir_text = str(raw_dir)

    if isinstance(payload, dict):
        payload_dict = cast(dict[object, object], payload)
        return {key: _sanitize_public_fixture_payload(value, raw_dir=raw_dir) for key, value in payload_dict.items()}
    if isinstance(payload, list):
        payload_list = cast(list[object], payload)
        return [_sanitize_public_fixture_payload(item, raw_dir=raw_dir) for item in payload_list]
    if isinstance(payload, str):
        if payload == raw_dir_text:
            return "<fixture-raw-dir>"
        if payload.startswith(raw_dir_text + "/"):
            return payload.replace(raw_dir_text, "<fixture-raw-dir>", 1)
    return payload


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh adapter-pack golden outputs through the typed services.",
    )
    parser.add_argument(
        "--pack-root",
        type=Path,
        default=DEFAULT_PACK_ROOT,
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


def collect_pack_outputs(pack: AdapterPack) -> dict[str, object]:
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    profile_use_case = build_profile_use_case()
    normalization_use_case = normalize_source_use_case()
    profile = profile_use_case.create_profile(pack.source, pack.raw_dir)
    adapter = registry.source_adapter(str(profile.adapter_id))
    location_inventory, wallet_issues = adapter.extract_location_inventory(pack.source, pack.raw_dir, profile)
    payloads: dict[str, object] = {
        "location_inventory": [record.to_row() for record in location_inventory],
        "wallet_issues": [issue.to_row() for issue in wallet_issues],
    }
    with TemporaryDirectory(prefix="tallylot-pack-refresh-") as temp_dir_name:
        if pack.supports("normalize"):
            output_dir = Path(temp_dir_name) / "normalized"
            normalization_use_case.execute(
                NormalizeRequest(
                    source=pack.source,
                    raw_dir=pack.raw_dir,
                    output_dir=output_dir,
                )
            )
            payloads.update(
                {
                    "facts": artifacts.read_rows(output_dir / "facts.csv"),
                    "fact_annotations": json.loads((output_dir / "fact_annotations.json").read_text(encoding="utf-8")),
                    "location_annotations": json.loads(
                        (output_dir / "location_annotations.json").read_text(encoding="utf-8")
                    ),
                    "balances": artifacts.read_rows(output_dir / "balances.csv"),
                    "balance_evidence": artifacts.read_rows(output_dir / "balance_evidence.csv"),
                    "exceptions": artifacts.read_rows(output_dir / "exceptions.csv"),
                    "normalization_reviews": artifacts.read_rows(output_dir / "normalization_reviews.csv"),
                    "normalization_summary": json.loads(
                        (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
                    ),
                }
            )
        return {
            artifact_name: _sanitize_public_fixture_payload(payload, raw_dir=pack.raw_dir)
            for artifact_name, payload in payloads.items()
        }


def refresh_pack(pack: AdapterPack) -> tuple[Path, ...]:
    payloads = collect_pack_outputs(pack)
    pack.expected_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    artifact_names: tuple[str, ...] = EXPECTED_LOCATION_ARTIFACTS
    if pack.supports("normalize"):
        artifact_names = EXPECTED_NORMALIZATION_ARTIFACTS + EXPECTED_LOCATION_ARTIFACTS
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
    packs = select_adapter_packs(
        pack_root=args.pack_root.resolve(),
        selected_ids=tuple(args.packs),
        capability=args.capability,
    )
    if not packs:
        print("No adapter packs matched the requested filters.")
        return 0
    for pack in packs:
        print(f"Refreshing {pack.id}")
        for path in refresh_pack(pack):
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
