from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId


def test_balance_snapshot_requires_temporal_value() -> None:
    with pytest.raises(ValueError, match="balance snapshot as_of_at must be timezone-aware UTC"):
        BalanceSnapshot(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime.fromisoformat("2025-01-01T00:00:00"),
            as_of_precision=TemporalPrecision.TIMESTAMP,
        )

    snapshot = BalanceSnapshot(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        instrument_id=InstrumentId("symbol:BTC"),
        quantity=Decimal("1"),
        as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        as_of_precision=TemporalPrecision.TIMESTAMP,
    )

    assert snapshot.as_of_at.tzinfo is UTC


def test_balance_evidence_requires_temporal_value() -> None:
    with pytest.raises(ValueError, match="balance evidence as_of_at must be timezone-aware UTC"):
        BalanceEvidence(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime.fromisoformat("2025-01-01T00:00:00-06:00"),
            as_of_precision=TemporalPrecision.TIMESTAMP,
        )

    evidence = BalanceEvidence(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        instrument_id=InstrumentId("symbol:BTC"),
        quantity=Decimal("1"),
        as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        as_of_precision=TemporalPrecision.TIMESTAMP,
    )

    assert evidence.as_of_at.tzinfo is UTC
