from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.types import AssetSymbol, LocationId, SourceId


def test_balance_snapshot_requires_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="balance snapshot as_of must be timezone-aware UTC"):
        BalanceSnapshot(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            asset=AssetSymbol("BTC"),
            quantity=Decimal("1"),
            as_of=datetime.fromisoformat("2025-01-01T00:00:00"),
        )

    snapshot = BalanceSnapshot(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        asset=AssetSymbol("BTC"),
        quantity=Decimal("1"),
        as_of=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    assert snapshot.as_of.tzinfo is UTC


def test_balance_evidence_requires_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="balance evidence as_of must be timezone-aware UTC"):
        BalanceEvidence(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            asset=AssetSymbol("BTC"),
            quantity=Decimal("1"),
            as_of=datetime.fromisoformat("2025-01-01T00:00:00-06:00"),
        )

    evidence = BalanceEvidence(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        asset=AssetSymbol("BTC"),
        quantity=Decimal("1"),
        as_of=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
    )

    assert evidence.as_of.tzinfo is UTC
