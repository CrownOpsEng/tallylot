from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tallylot.infrastructure.storage.balance_codec import (
    balance_reference_from_row,
    balance_snapshot_from_row,
)
from tallylot.ports.evidence import BALANCE_REFERENCE_HEADER, BALANCE_SNAPSHOT_HEADER


def test_balance_snapshot_from_row_defaults_blank_balance_kind() -> None:
    snapshot = balance_snapshot_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "balance_kind": "",
            "target_at": "2025-12-31 23:59:59",
            "target_precision": "timestamp",
            "quantity": "1.25",
            "snapshot_basis": "fact_cutoff",
            "notes": "",
        }
    )

    assert snapshot.balance_kind == "available"
    assert snapshot.quantity == Decimal("1.25")
    assert snapshot.snapshot_basis == "fact_cutoff"


def test_balance_reference_from_row_defaults_blank_balance_kind() -> None:
    reference = balance_reference_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "balance_kind": "",
            "target_at": "2025-12-31",
            "target_precision": "date",
            "quantity": "1.25",
            "reference_kind": "source_document",
            "observed_at": "2025-12-31",
            "observed_precision": "date",
            "support_ref": "statement.pdf#page=1",
            "provider_family": "",
            "provider_locator": "",
            "provider_block_ref": "",
            "reviewed_by": "",
            "reviewed_at": "",
            "notes": "statement",
        }
    )

    assert reference.balance_kind == "available"
    assert reference.target_at == datetime(2025, 12, 31, tzinfo=UTC)
    assert reference.observed_at == datetime(2025, 12, 31, tzinfo=UTC)
    assert reference.support_ref == "statement.pdf#page=1"


def test_balance_reference_from_row_parses_network_api_reference_fields() -> None:
    reference = balance_reference_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "balance_kind": "available",
            "target_at": "2025-12-31 23:59:59",
            "target_precision": "timestamp",
            "quantity": "1.25",
            "reference_kind": "network_api",
            "observed_at": "2025-12-31 23:59:59",
            "observed_precision": "timestamp",
            "support_ref": "",
            "provider_family": "evm_json_rpc",
            "provider_locator": "rpc://example",
            "provider_block_ref": "block:123",
            "reviewed_by": "",
            "reviewed_at": "",
            "notes": "network",
        }
    )

    assert reference.reference_kind is BalanceReferenceKind.NETWORK_API
    assert reference.provider_family == "evm_json_rpc"
    assert reference.provider_locator == "rpc://example"
    assert reference.provider_block_ref == "block:123"
    assert reference.reviewed_at is None
    assert reference.notes == "network"


def test_balance_snapshot_from_row_rejects_missing_quantity() -> None:
    with pytest.raises(ValueError, match="missing required decimal field: quantity"):
        balance_snapshot_from_row(
            {
                "source": "coinbase",
                "location_id": "coinbase",
                "instrument_id": "BTC",
                "balance_kind": "available",
                "target_at": "2025-12-31 23:59:59",
                "target_precision": "timestamp",
                "quantity": "",
                "snapshot_basis": "fact_cutoff",
                "notes": "",
            }
        )


def test_balance_snapshot_repository_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "balance_snapshots.csv"
    repository = FilesystemEvidenceRepository()
    snapshots = (
        BalanceSnapshot(
            target=BalanceTarget(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase:primary"),
                instrument_id=InstrumentId("symbol:BTC@coinbase"),
                balance_kind="available",
                target_at=datetime(2025, 12, 31, tzinfo=UTC),
                target_precision=TemporalPrecision.DATE,
            ),
            quantity=Decimal("1.25"),
            snapshot_basis="fact_cutoff",
            notes="derived",
        ),
    )

    repository.write_balance_snapshots(path, snapshots)

    assert tuple(read_rows(path)[0].keys()) == BALANCE_SNAPSHOT_HEADER
    assert repository.read_balance_snapshots(path) == snapshots


def test_balance_reference_repository_round_trip_operator_assertion(
    tmp_path: Path,
) -> None:
    path = tmp_path / "balance_references.csv"
    repository = FilesystemEvidenceRepository()
    target = BalanceTarget(
        source=SourceId("coinbase"),
        location_id=LocationId("coinbase:primary"),
        instrument_id=InstrumentId("symbol:BTC@coinbase"),
        balance_kind="available",
        target_at=datetime(2025, 12, 31, tzinfo=UTC),
        target_precision=TemporalPrecision.DATE,
    )
    references = (
        BalanceReference(
            target=target,
            quantity=Decimal("1.25"),
            reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
            observed_at=datetime(2025, 12, 31, tzinfo=UTC),
            observed_precision=TemporalPrecision.DATE,
            support_ref="statement.pdf#page=1",
            reviewed_by="operator",
            reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            notes="manual review",
        ),
    )

    repository.write_balance_references(path, references)

    rows = read_rows(path)

    assert tuple(rows[0].keys()) == BALANCE_REFERENCE_HEADER
    assert rows[0]["reference_kind"] == "operator_assertion"
    assert rows[0]["support_ref"] == "statement.pdf#page=1"
    assert repository.read_balance_references(path) == references
