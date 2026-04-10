from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceConfirmation
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.infrastructure.storage.balance_codec import (
    balance_confirmation_from_row,
    balance_evidence_from_row,
    balance_snapshot_from_row,
)
from tallylot.infrastructure.storage import FilesystemEvidenceRepository
from tallylot.infrastructure.serialization.csv_io import read_rows
from tallylot.ports.evidence import BALANCE_CONFIRMATION_HEADER


def test_balance_snapshot_from_row_defaults_blank_balance_kind() -> None:
    snapshot = balance_snapshot_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "quantity": "1.25",
            "as_of_at": "2025-12-31 23:59:59",
            "as_of_precision": "timestamp",
            "balance_kind": "",
            "notes": "",
        }
    )

    assert snapshot.balance_kind == "available"
    assert snapshot.quantity == Decimal("1.25")


def test_balance_evidence_from_row_defaults_blank_balance_kind() -> None:
    evidence = balance_evidence_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "quantity": "1.25",
            "as_of_at": "2025-12-31",
            "as_of_precision": "date",
            "balance_kind": "",
            "evidence_ref": "statement.pdf",
            "notes": "statement",
        }
    )

    assert evidence.balance_kind == "available"
    assert evidence.as_of_at == datetime(2025, 12, 31, tzinfo=UTC)
    assert evidence.evidence_ref == "statement.pdf"


def test_balance_confirmation_from_row_defaults_blank_balance_kind() -> None:
    confirmation = balance_confirmation_from_row(
        {
            "source": "coinbase",
            "location_id": "coinbase",
            "instrument_id": "BTC",
            "quantity": "1.25",
            "as_of_at": "2025-12-31",
            "as_of_precision": "date",
            "balance_kind": "",
            "confirmation_kind": "external_support",
            "support_ref": "statement.pdf#page=1",
            "asserted_meaning": "Closing balance from the cited statement.",
            "reviewed_by": "operator",
            "reviewed_at": "2026-01-01 00:00:00",
            "reason": "Needed for runtime reconciliation.",
            "notes": "manual review",
        }
    )

    assert confirmation.balance_kind == "available"
    assert confirmation.as_of_at == datetime(2025, 12, 31, tzinfo=UTC)
    assert confirmation.reviewed_at == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert confirmation.support_ref == "statement.pdf#page=1"


def test_balance_confirmation_repository_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "balance_confirmations.csv"
    repository = FilesystemEvidenceRepository()
    confirmations = (
        BalanceConfirmation(
            source=SourceId("coinbase"),
            location_id=LocationId("coinbase:primary"),
            instrument_id=InstrumentId("symbol:BTC@coinbase"),
            quantity=Decimal("1.25"),
            as_of_at=datetime(2025, 12, 31, tzinfo=UTC),
            as_of_precision=TemporalPrecision.DATE,
            balance_kind="available",
            confirmation_kind="external_support",
            support_ref="statement.pdf#page=1",
            asserted_meaning="Closing balance from the cited statement.",
            reviewed_by="operator",
            reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
            notes="manual review",
        ),
    )

    repository.write_balance_confirmations(path, confirmations)

    assert tuple(read_rows(path)[0].keys()) == BALANCE_CONFIRMATION_HEADER
    assert repository.read_balance_confirmations(path) == confirmations
