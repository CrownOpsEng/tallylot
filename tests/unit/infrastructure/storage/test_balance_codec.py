from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.infrastructure.storage.balance_codec import (
    balance_evidence_from_row,
    balance_snapshot_from_row,
)


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
