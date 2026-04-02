from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from crypto_reconciliation.application.dtos import NormalizeRequest, ProfileRequest
from crypto_reconciliation.application.services.normalize import (
    NormalizationDependencies,
    NormalizationService,
)
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
from crypto_reconciliation.ports.adapters import NormalizationResult, SourceAdapter, SourceAdapterRegistryPort


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


def _normalization_service(
    registry: SourceAdapterRegistryPort,
    artifacts: FilesystemArtifactStore,
) -> NormalizationService:
    runtime_registry = build_registry()
    return NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=runtime_registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )


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


def test_profile_service_rejects_missing_source_directories(tmp_path: Path) -> None:
    registry = FakeSourceRegistry(source_adapters=(MatchingSourceAdapter("alpha_adapter"),))
    service = ProfileService(registry, FilesystemArtifactStore())

    with pytest.raises(FileNotFoundError, match="raw source directory does not exist"):
        service.create_profile("fixture", tmp_path / "missing")


def test_normalization_service_rejects_unsupported_adapters(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(source_adapters=(MatchingSourceAdapter("unsupported", supported=False),))
    artifacts = FilesystemArtifactStore()
    service = _normalization_service(registry, artifacts)

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
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.event_count == 1
    assert response.issue_count == 1
    assert response.review_count == 2

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    wallet_rows = artifacts.read_rows(output_dir / "wallet_inventory.csv")

    assert exception_rows[0]["kind"] == "invalid_decimal"
    assert [row["kind"] for row in review_rows] == [
        "timestamp_timezone_assumed_utc",
        "default_render_mapping",
    ]
    assert wallet_rows[0]["evidence_path"] == "transactions.csv"
    assert (output_dir / "cointracking_candidate.csv").exists()
    assert (output_dir / "timezone_issues.csv").exists()


def test_structured_csv_normalization_rejects_zero_amounts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,Trade,BTC,0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.event_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == ["zero_amount", "no_valid_rows"]
    assert not review_rows


def test_structured_csv_normalization_canonicalizes_signed_amounts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,Trade,BTC,1.5,CAD,-10.0,CAD,-0.1,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.event_count == 1
    assert response.issue_count == 0
    assert response.review_count == 4

    canonical_rows = artifacts.read_rows(output_dir / "canonical_events.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))

    assert canonical_rows[0]["amount_in"] == "1.5"
    assert canonical_rows[0]["amount_out"] == "10"
    assert canonical_rows[0]["fee_amount"] == "0.1"
    assert [row["kind"] for row in review_rows] == [
        "outbound_amount_sign_canonicalized",
        "outbound_amount_sign_canonicalized",
        "timestamp_timezone_assumed_utc",
        "default_render_mapping",
    ]
    assert review_rows[0]["field_name"] == "amount_out"
    assert review_rows[0]["original_value"] == "-10.0"
    assert review_rows[0]["normalized_value"] == "10"
    assert review_rows[1]["field_name"] == "fee_amount"
    assert review_rows[1]["original_value"] == "-0.1"
    assert review_rows[1]["normalized_value"] == "0.1"
    assert summary["review_count"] == 4
    assert summary["review_summary"] == [
        {
            "scope": "dataset",
            "kind": "default_render_mapping",
            "count": 1,
            "field_names": [],
            "messages": [
                (
                    "Structured CSV normalization defaults CoinTracking render fields to "
                    "render_type<-event_kind, render_exchange<-account, and "
                    "render_comment<-description; validate those mappings before import."
                )
            ],
        },
        {
            "scope": "dataset",
            "kind": "timestamp_timezone_assumed_utc",
            "count": 1,
            "field_names": [],
            "messages": [
                (
                    "Structured CSV timestamps are timezone-naive; normalization assigns UTC "
                    "and those timestamps should be validated against the source system."
                )
            ],
        },
        {
            "scope": "row",
            "kind": "outbound_amount_sign_canonicalized",
            "count": 2,
            "field_names": ["amount_out", "fee_amount"],
            "messages": [
                "amount_out was negative and was canonicalized to a positive outbound value.",
                "fee_amount was negative and was canonicalized to a positive outbound value.",
            ],
        },
    ]


def test_structured_csv_normalization_rejects_conflicting_inbound_signs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,Trade,BTC,-1.5,,,,,tx-1,BTC transfer,Fixture,Primary\n",
        encoding="utf-8",
    )
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.event_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == [
        "conflicting_amount_sign",
        "no_valid_rows",
    ]
    assert not review_rows


def test_profile_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
            "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    service = ProfileService(registry, FilesystemArtifactStore())

    with pytest.raises(
        ValueError,
        match="profile output directory must not be inside raw source directory",
    ):
        service.execute(
            ProfileRequest(
                source="fixture_source",
                raw_dir=raw_dir,
                output_dir=raw_dir / "profile",
            )
        )


def test_normalization_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,event_kind,asset_in,amount_in,asset_out,amount_out,"
            "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
            "2023-08-06 10:00:00,Trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    registry = build_registry()
    artifacts = FilesystemArtifactStore()
    service = NormalizationService(
        NormalizationDependencies(
            source_registry=registry,
            output_registry=registry,
            profile_service=ProfileService(registry, artifacts),
            storage=FilesystemStorage(),
            artifacts=artifacts,
        )
    )

    with pytest.raises(
        ValueError,
        match="normalization output directory must not be inside raw source directory",
    ):
        service.execute(
            NormalizeRequest(
                source="fixture_source",
                raw_dir=raw_dir,
                output_dir=raw_dir / "normalized",
            )
        )
