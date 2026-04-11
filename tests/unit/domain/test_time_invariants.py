from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

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


def test_balance_target_requires_temporal_value() -> None:
    with pytest.raises(
        ValueError, match="balance target target_at must be timezone-aware UTC"
    ):
        BalanceTarget(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            balance_kind="available",
            target_at=datetime.fromisoformat("2025-01-01T00:00:00"),
            target_precision=TemporalPrecision.TIMESTAMP,
        )

    target = BalanceTarget(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        instrument_id=InstrumentId("symbol:BTC"),
        balance_kind="available",
        target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        target_precision=TemporalPrecision.TIMESTAMP,
    )

    assert target.target_at.tzinfo is UTC


def test_balance_target_requires_non_blank_instrument_id() -> None:
    with pytest.raises(
        ValueError, match="balance target instrument_id must not be blank"
    ):
        BalanceTarget(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId(""),
            balance_kind="available",
            target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            target_precision=TemporalPrecision.TIMESTAMP,
        )


def test_balance_snapshot_requires_non_blank_basis() -> None:
    with pytest.raises(
        ValueError, match="balance snapshot snapshot_basis must not be blank"
    ):
        BalanceSnapshot(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            snapshot_basis=" ",
        )

    snapshot = BalanceSnapshot(
        target=BalanceTarget(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            balance_kind="available",
            target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal("1"),
        snapshot_basis="fact_cutoff",
    )

    assert snapshot.target_at.tzinfo is UTC


def test_balance_reference_requires_temporal_values_and_kind_rules() -> None:
    with pytest.raises(
        ValueError, match="balance reference observed_at must be timezone-aware UTC"
    ):
        BalanceReference(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            observed_at=datetime.fromisoformat("2025-01-01T00:00:00-06:00"),
            observed_precision=TemporalPrecision.TIMESTAMP,
        )

    with pytest.raises(
        ValueError, match="operator assertion balance references require reviewed_by"
    ):
        BalanceReference(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
            observed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            observed_precision=TemporalPrecision.TIMESTAMP,
        )

    with pytest.raises(
        ValueError, match="network api balance references require provider_family"
    ):
        BalanceReference(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            reference_kind=BalanceReferenceKind.NETWORK_API,
            observed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            observed_precision=TemporalPrecision.TIMESTAMP,
        )

    reference = BalanceReference(
        target=BalanceTarget(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            balance_kind="available",
            target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            target_precision=TemporalPrecision.TIMESTAMP,
        ),
        quantity=Decimal("1"),
        reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
        observed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        observed_precision=TemporalPrecision.TIMESTAMP,
        support_ref="statement.pdf#page=1",
        reviewed_by="operator",
        reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
    )

    assert reference.observed_at.tzinfo is UTC
    assert reference.reviewed_at is not None
    assert reference.reviewed_at.tzinfo is UTC


def test_balance_reference_rejects_invalid_reviewed_fields() -> None:
    with pytest.raises(
        ValueError, match="balance reference reviewed_at requires reviewed_by"
    ):
        BalanceReference(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            observed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            observed_precision=TemporalPrecision.TIMESTAMP,
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        )

    with pytest.raises(
        ValueError, match="only network api balance references may set provider fields"
    ):
        BalanceReference(
            target=BalanceTarget(
                source=SourceId("fixture"),
                location_id=LocationId("taxable:spot"),
                instrument_id=InstrumentId("symbol:BTC"),
                balance_kind="available",
                target_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                target_precision=TemporalPrecision.TIMESTAMP,
            ),
            quantity=Decimal("1"),
            reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
            observed_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            observed_precision=TemporalPrecision.TIMESTAMP,
            provider_family="evm_json_rpc",
        )
