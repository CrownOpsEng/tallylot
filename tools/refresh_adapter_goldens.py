from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from crypto_reconciliation.application.dtos import NormalizeRequest
from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.infrastructure.discovery.adapters import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage.filesystem import FilesystemStorage
from tools.adapter_packs import DEFAULT_PACK_ROOT, AdapterPack, select_adapter_packs

EXPECTED_ARTIFACTS = (
    "canonical_events",
    "canonical_balances",
    "exceptions",
    "normalization_reviews",
    "wallet_inventory",
    "normalization_summary",
)


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
        help="Filter packs by capability such as 'normalize' or 'wallet_inventory'.",
    )
    return parser


def collect_pack_outputs(pack: AdapterPack) -> dict[str, object]:
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    normalization_service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    with TemporaryDirectory(prefix="crypto-recon-pack-refresh-") as temp_dir_name:
        output_dir = Path(temp_dir_name) / "normalized"
        normalization_service.execute(
            NormalizeRequest(
                source=pack.source,
                raw_dir=pack.raw_dir,
                output_dir=output_dir,
            )
        )
        return {
            "canonical_events": artifacts.read_rows(output_dir / "canonical_events.csv"),
            "canonical_balances": artifacts.read_rows(output_dir / "canonical_balances.csv"),
            "exceptions": artifacts.read_rows(output_dir / "exceptions.csv"),
            "normalization_reviews": artifacts.read_rows(output_dir / "normalization_reviews.csv"),
            "wallet_inventory": artifacts.read_rows(output_dir / "wallet_inventory.csv"),
            "normalization_summary": json.loads(
                (output_dir / "normalization_summary.json").read_text(encoding="utf-8")
            ),
        }


def refresh_pack(pack: AdapterPack) -> tuple[Path, ...]:
    payloads = collect_pack_outputs(pack)
    pack.expected_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    for artifact_name in EXPECTED_ARTIFACTS:
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
