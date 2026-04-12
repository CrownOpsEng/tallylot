from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tallylot.application.checkpoints.balance_submission.contracts import (
    BalanceReferenceSubmissionRow,
    BalanceSnapshotSubmissionRow,
    LocationInventorySubmissionRow,
)
from tallylot.domain.balances import BalanceReferenceKind
from tallylot.domain.temporal import TemporalPrecision


def test_balance_snapshot_submission_row_strips_and_normalizes_fields() -> None:
    row = BalanceSnapshotSubmissionRow(
        source=" coinbase ",
        account=" primary ",
        wallet=" primary ",
        instrument_id=" symbol:BTC ",
        quantity=Decimal("1.25"),
        target_at=datetime(2026, 3, 23, 12, 0, 0, tzinfo=UTC),
        target_precision=TemporalPrecision.TIMESTAMP,
        balance_kind=" available ",
        notes=" note ",
    )

    assert row.source == "coinbase"
    assert row.account == "primary"
    assert row.wallet == "primary"
    assert row.instrument_id == "symbol:BTC"
    assert row.balance_kind == "available"
    assert row.notes == "note"


def test_balance_reference_submission_row_parses_reference_kind() -> None:
    row = BalanceReferenceSubmissionRow.model_validate(
        {
            "source": "coinbase",
            "account": "primary",
            "wallet": "primary",
            "instrument_id": "symbol:BTC",
            "quantity": Decimal("1.25"),
            "target_at": datetime(2026, 3, 23, 12, 0, 0, tzinfo=UTC),
            "target_precision": TemporalPrecision.TIMESTAMP,
            "balance_kind": "available",
            "reference_kind": "operator_assertion",
            "observed_at": datetime(2026, 3, 23, 12, 0, 0, tzinfo=UTC),
            "observed_precision": TemporalPrecision.TIMESTAMP,
            "reviewed_by": " operator@example.com ",
            "reviewed_at": datetime(2026, 3, 23, 13, 0, 0, tzinfo=UTC),
        }
    )

    assert row.reference_kind is BalanceReferenceKind.OPERATOR_ASSERTION
    assert row.reviewed_by == "operator@example.com"


def test_location_inventory_submission_row_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LocationInventorySubmissionRow.model_validate(
            {
                "source": "coinbase",
                "account": "primary",
                "wallet": "primary",
                "identifier_kind": "address",
                "identifier_value": "0x1111111111111111111111111111111111111111",
                "confidence": "high",
                "extra_field": "not-allowed",
            }
        )
