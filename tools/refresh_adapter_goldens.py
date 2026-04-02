from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from crypto_reconciliation.application.models.source import NormalizeRequest
from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.infrastructure.discovery.adapters import build_registry
from crypto_reconciliation.infrastructure.serialization import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage.filesystem import FilesystemStorage
from tools.adapter_packs import DEFAULT_PACK_ROOT, AdapterPack, select_adapter_packs

EXPECTED_NORMALIZATION_ARTIFACTS = (
    "canonical_events",
    "canonical_balances",
    "exceptions",
    "normalization_reviews",
    "normalization_summary",
)
EXPECTED_WALLET_ARTIFACTS = (
    "wallet_inventory",
    "wallet_issues",
)
EXPECTED_ARTIFACTS = EXPECTED_NORMALIZATION_ARTIFACTS + EXPECTED_WALLET_ARTIFACTS


def _sanitize_public_fixture_payload(payload: object, *, raw_dir: Path) -> object:
    raw_dir_text = str(raw_dir)

    if isinstance(payload, dict):
        return {key: _sanitize_public_fixture_payload(value, raw_dir=raw_dir) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_sanitize_public_fixture_payload(item, raw_dir=raw_dir) for item in payload]
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
        help="Filter packs by capability such as 'normalize' or 'wallet_inventory'.",
    )
    return parser


def collect_pack_outputs(pack: AdapterPack) -> dict[str, object]:
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    profile_service = ProfileService(registry, artifacts)
    normalization_service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            profile_service=profile_service,
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    profile = profile_service.create_profile(pack.source, pack.raw_dir)
    adapter = registry.source_adapter(str(profile.adapter_id))
    wallet_inventory, wallet_issues = adapter.extract_wallet_inventory(pack.source, pack.raw_dir, profile)
    payloads: dict[str, object] = {
        "wallet_inventory": [record.to_row() for record in wallet_inventory],
        "wallet_issues": [issue.to_row() for issue in wallet_issues],
    }
    with TemporaryDirectory(prefix="crypto-recon-pack-refresh-") as temp_dir_name:
        if pack.supports("normalize"):
            output_dir = Path(temp_dir_name) / "normalized"
            normalization_service.execute(
                NormalizeRequest(
                    source=pack.source,
                    raw_dir=pack.raw_dir,
                    output_dir=output_dir,
                )
            )
            payloads.update(
                {
                    "canonical_events": artifacts.read_rows(output_dir / "canonical_events.csv"),
                    "canonical_balances": artifacts.read_rows(output_dir / "canonical_balances.csv"),
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
    artifact_names: tuple[str, ...] = EXPECTED_WALLET_ARTIFACTS
    if pack.supports("normalize"):
        artifact_names = EXPECTED_NORMALIZATION_ARTIFACTS + EXPECTED_WALLET_ARTIFACTS
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
