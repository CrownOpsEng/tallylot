from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from crypto_reconciliation.application.dtos import NormalizeRequest
from crypto_reconciliation.application.services.normalize import NormalizationService
from crypto_reconciliation.application.services.profile import ProfileService
from crypto_reconciliation.domain.models import (
    AdapterCapability,
    AdapterManifest,
    FileInventoryEntry,
)
from crypto_reconciliation.domain.types import AdapterId
from crypto_reconciliation.infrastructure.discovery import build_registry
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.infrastructure.storage import FilesystemStorage
from crypto_reconciliation.ports.adapters import NormalizationResult, SourceAdapter


@dataclass(frozen=True)
class FakeSourceRegistry:
    source_adapters: tuple[SourceAdapter, ...]

    def source_adapter(self, adapter_id: str) -> SourceAdapter:
        for adapter in self.source_adapters:
            if str(adapter.manifest.adapter_id) == adapter_id:
                return adapter
        raise KeyError(adapter_id)


class MatchingSourceAdapter:
    def __init__(self, adapter_id: str, *, supported: bool = True) -> None:
        self.manifest = AdapterManifest(
            adapter_id=AdapterId(adapter_id),
            display_name=adapter_id,
            version="1.0.0",
            capabilities=frozenset({AdapterCapability.NORMALIZE}),
            supported=supported,
        )

    def match(self, source: str, raw_dir: Path, inventory: tuple[FileInventoryEntry, ...]) -> int:
        del source, raw_dir, inventory
        return 100

    def normalize(self, profile: object, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        raise AssertionError("normalize should not be called in this test")


def test_profile_service_rejects_ambiguous_adapter_matches(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(
        source_adapters=(
            MatchingSourceAdapter("alpha_adapter"),
            MatchingSourceAdapter("beta_adapter"),
        )
    )

    service = ProfileService(registry, FilesystemArtifactStore())

    with pytest.raises(ValueError, match="ambiguous source adapter match"):
        service.create_profile("fixture", raw_dir)


def test_normalization_service_rejects_unsupported_adapters(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(
        source_adapters=(MatchingSourceAdapter("unsupported", supported=False),)
    )
    artifacts = FilesystemArtifactStore()
    profile_service = ProfileService(registry, artifacts)
    service = NormalizationService(registry, profile_service, FilesystemStorage(), artifacts)

    with pytest.raises(ValueError, match="is not supported for normalization"):
        service.execute(
            NormalizeRequest(
                source="fixture",
                raw_dir=raw_dir,
                output_dir=tmp_path / "normalized",
            )
        )


def test_structured_csv_normalization_surfaces_invalid_rows_as_issues(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,Trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n"
        + "2023-08-07 15:00:00,Income,ETH,not-a-decimal,,,,,tx-2,ETH reward,Fixture,Primary\n",
        encoding="utf-8",
    )
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    service = NormalizationService(
        registry,
        ProfileService(registry, artifacts),
        FilesystemStorage(),
        artifacts,
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir)
    )

    assert response.event_count == 1
    assert response.issue_count == 1

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    wallet_rows = artifacts.read_rows(output_dir / "wallet_inventory.csv")

    assert exception_rows[0]["kind"] == "invalid_decimal"
    assert wallet_rows[0]["evidence_path"] == "transactions.csv"
