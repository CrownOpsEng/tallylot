from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import override

import pytest

from crypto_reconciliation.application.models.source import NormalizeRequest
from crypto_reconciliation.domain.models import BalanceEvidence, NormalizedTransaction
from crypto_reconciliation.domain.transactions import ProjectionType
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from crypto_reconciliation.ports.adapters import NormalizationResult
from tests.support.services import (
    FakeSourceRegistry,
    MatchingSourceAdapter,
    build_normalization_service,
    build_registry_backed_normalization_service,
)


def test_normalization_service_rejects_unsupported_adapters(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(source_adapters=(MatchingSourceAdapter("unsupported", supported=False),))
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(registry=registry, artifacts=artifacts)

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
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header
        + "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n"
        + "2023-08-07 15:00:00,reward,ETH,not-a-decimal,,,,,tx-2,ETH reward,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.transaction_count == 1
    assert response.issue_count == 1
    assert response.review_count == 1

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    wallet_rows = artifacts.read_rows(output_dir / "wallet_inventory.csv")

    assert exception_rows[0]["kind"] == "invalid_decimal"
    assert [row["kind"] for row in review_rows] == ["timestamp_timezone_assumed_utc"]
    assert wallet_rows[0]["evidence_path"] == "transactions.csv"
    assert (output_dir / "timezone_issues.csv").exists()


def test_structured_csv_normalization_rejects_zero_amounts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,trade,BTC,0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.transaction_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == ["zero_amount", "no_valid_rows"]
    assert not review_rows


def test_structured_csv_normalization_normalizes_signed_amounts(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,trade,BTC,1.5,CAD,-10.0,CAD,-0.1,tx-1,BTC buy,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.transaction_count == 1
    assert response.issue_count == 0
    assert response.review_count == 3

    transaction_rows = artifacts.read_rows(output_dir / "transactions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))

    assert transaction_rows[0]["amount_in"] == "1.5"
    assert transaction_rows[0]["amount_out"] == "10"
    assert transaction_rows[0]["fee_amount"] == "0.1"
    assert [row["kind"] for row in review_rows] == [
        "outbound_amount_sign_normalized",
        "outbound_amount_sign_normalized",
        "timestamp_timezone_assumed_utc",
    ]
    assert review_rows[0]["field_name"] == "amount_out"
    assert review_rows[0]["original_value"] == "-10.0"
    assert review_rows[0]["normalized_value"] == "10"
    assert review_rows[1]["field_name"] == "fee_amount"
    assert review_rows[1]["original_value"] == "-0.1"
    assert review_rows[1]["normalized_value"] == "0.1"
    assert summary["review_count"] == 3
    assert summary["review_summary"] == [
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
            "kind": "outbound_amount_sign_normalized",
            "count": 2,
            "field_names": ["amount_out", "fee_amount"],
            "messages": [
                "amount_out was negative and was normalized to a positive outbound value.",
                "fee_amount was negative and was normalized to a positive outbound value.",
            ],
        },
    ]


def test_structured_csv_normalization_rejects_conflicting_inbound_signs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    header = (
        "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
        "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
    )
    (raw_dir / "transactions.csv").write_text(
        header + "2023-08-06 10:00:00,trade,BTC,-1.5,,,,,tx-1,BTC transfer,Fixture,Primary\n",
        encoding="utf-8",
    )
    artifacts = FilesystemArtifactStore()
    service = build_normalization_service(artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(NormalizeRequest(source="fixture_source", raw_dir=raw_dir, output_dir=output_dir))

    assert response.transaction_count == 0
    assert response.issue_count == 2
    assert response.review_count == 0

    exception_rows = artifacts.read_rows(output_dir / "exceptions.csv")
    review_rows = artifacts.read_rows(output_dir / "normalization_reviews.csv")

    assert [row["kind"] for row in exception_rows] == [
        "conflicting_amount_sign",
        "no_valid_rows",
    ]
    assert not review_rows


def test_normalization_service_rejects_output_inside_raw_tree(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "transactions.csv").write_text(
        (
            "timestamp,category,asset_in,amount_in,asset_out,amount_out,"
            "fee_asset,fee_amount,tx_hash,description,account,wallet\n"
            "2023-08-06 10:00:00,trade,BTC,1.0,CAD,10.0,CAD,0.1,tx-1,BTC buy,Fixture,Primary\n"
        ),
        encoding="utf-8",
    )
    service = build_normalization_service(artifacts=FilesystemArtifactStore())

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


class EvidenceSourceAdapter(MatchingSourceAdapter):
    @override
    def normalize(self, profile: object, raw_dir: Path) -> NormalizationResult:
        del profile, raw_dir
        return NormalizationResult(
            transactions=(
                NormalizedTransaction(
                    transaction_id=TransactionId("txn-1"),
                    source=SourceId("fixture"),
                    adapter_id=AdapterId("evidence_fixture"),
                    account="Fixture",
                    wallet="Primary",
                    timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
                    category="deposit",
                    projection_type=ProjectionType.DEPOSIT,
                    asset_in=AssetSymbol("BTC"),
                    amount_in=Decimal("1.5"),
                    tx_hash="tx-1",
                ),
            ),
            balance_evidence=(
                BalanceEvidence(
                    source=SourceId("fixture"),
                    account="Fixture",
                    wallet="Primary",
                    asset=AssetSymbol("BTC"),
                    quantity=Decimal("2.5"),
                    as_of=datetime(2023, 8, 6, 12, 0, 0, tzinfo=UTC),
                    evidence_ref="statement:page:1",
                ),
            ),
            issues=(),
            reviews=(),
            wallet_inventory=(),
        )


def test_normalization_service_persists_balance_evidence_separately_from_derived_balances(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    registry = FakeSourceRegistry(source_adapters=(EvidenceSourceAdapter("evidence_fixture"),))
    artifacts = FilesystemArtifactStore()
    service = build_registry_backed_normalization_service(registry=registry, artifacts=artifacts)
    output_dir = tmp_path / "normalized"

    response = service.execute(
        NormalizeRequest(
            source="fixture",
            raw_dir=raw_dir,
            output_dir=output_dir,
        )
    )

    balance_rows = artifacts.read_rows(output_dir / "balances.csv")
    balance_evidence_rows = artifacts.read_rows(output_dir / "balance_evidence.csv")
    summary = json.loads((output_dir / "normalization_summary.json").read_text(encoding="utf-8"))

    assert response.balance_count == 1
    assert balance_rows == [
        {
            "source": "fixture",
            "account": "Fixture",
            "wallet": "Primary",
            "asset": "BTC",
            "quantity": "1.5",
            "as_of": "2023-08-06 10:00:00",
            "balance_kind": "available",
            "notes": "",
        }
    ]
    assert balance_evidence_rows == [
        {
            "source": "fixture",
            "account": "Fixture",
            "wallet": "Primary",
            "asset": "BTC",
            "quantity": "2.5",
            "as_of": "2023-08-06 12:00:00",
            "balance_kind": "available",
            "evidence_ref": "statement:page:1",
            "notes": "",
        }
    ]
    assert summary["balance_count"] == 1
    assert summary["balance_evidence_count"] == 1
