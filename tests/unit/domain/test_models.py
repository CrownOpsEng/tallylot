from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from crypto_reconciliation.domain.models import NormalizedTransaction
from crypto_reconciliation.domain.transactions import ProjectionType
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId


def _valid_transaction() -> NormalizedTransaction:
    return NormalizedTransaction(
        transaction_id=TransactionId("transaction-1"),
        source=SourceId("fixture"),
        adapter_id=AdapterId("structured_csv"),
        account="Fixture",
        wallet="Primary",
        timestamp=datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC),
        category="trade",
        asset_in=AssetSymbol("BTC"),
        amount_in=Decimal("1"),
    )


def test_transaction_rejects_incomplete_asset_amount_pairs() -> None:
    with pytest.raises(ValueError, match="asset_in and amount_in must both be present"):
        replace(_valid_transaction(), amount_in=None)

    with pytest.raises(ValueError, match="asset_out and amount_out must both be present"):
        replace(_valid_transaction(), asset_out=AssetSymbol("CAD"))

    with pytest.raises(ValueError, match="fee_asset and fee_amount must both be present"):
        replace(_valid_transaction(), fee_amount=Decimal("0.1"))


def test_transaction_rejects_non_positive_amounts() -> None:
    with pytest.raises(ValueError, match="amount_in must be greater than zero"):
        replace(_valid_transaction(), amount_in=Decimal("0"))

    with pytest.raises(ValueError, match="amount_out must be greater than zero"):
        replace(
            _valid_transaction(),
            asset_in=None,
            amount_in=None,
            asset_out=AssetSymbol("CAD"),
            amount_out=Decimal("-10"),
        )

    with pytest.raises(ValueError, match="fee_amount must be greater than zero"):
        replace(_valid_transaction(), fee_asset=AssetSymbol("CAD"), fee_amount=Decimal("0"))


def test_transaction_to_row_formats_fields() -> None:
    row = replace(
        _valid_transaction(),
        projection_type=ProjectionType.TRADE,
        operation_group_id="bundle-1",
        fee_asset=AssetSymbol("CAD"),
        fee_amount=Decimal("0.10000000"),
    ).to_row()

    assert row["timestamp"] == "2023-08-06 10:00:00"
    assert row["amount_in"] == "1"
    assert row["fee_amount"] == "0.1"
    assert row["account"] == "Fixture"
    assert row["projection_type"] == "Trade"
    assert row["operation_group_id"] == "bundle-1"
