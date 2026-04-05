from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId


def test_balance_snapshot_requires_temporal_value() -> None:
    with pytest.raises(
        ValueError, match="balance snapshot as_of_at must be timezone-aware UTC"
    ):
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


def test_balance_snapshot_requires_non_blank_instrument_id() -> None:
    with pytest.raises(
        ValueError, match="balance snapshot instrument_id must not be blank"
    ):
        BalanceSnapshot(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId(""),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
        )


def test_balance_evidence_requires_temporal_value() -> None:
    with pytest.raises(
        ValueError, match="balance evidence as_of_at must be timezone-aware UTC"
    ):
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


def test_balance_evidence_requires_non_blank_instrument_id() -> None:
    with pytest.raises(
        ValueError, match="balance evidence instrument_id must not be blank"
    ):
        BalanceEvidence(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId(""),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
        )


def test_balance_confirmation_requires_temporal_values_and_support_rules() -> None:
    with pytest.raises(
        ValueError, match="balance confirmation as_of_at must be timezone-aware UTC"
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime.fromisoformat("2025-01-01T00:00:00-06:00"),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="external_support",
            support_ref="statement.pdf#page=1",
            asserted_meaning="Closing balance from the cited statement.",
            reviewed_by="operator",
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
        )

    with pytest.raises(
        ValueError, match="balance confirmation reviewed_at must be timezone-aware UTC"
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="external_support",
            support_ref="statement.pdf#page=1",
            asserted_meaning="Closing balance from the cited statement.",
            reviewed_by="operator",
            reviewed_at=datetime.fromisoformat("2025-01-02T00:00:00-06:00"),
            reason="Needed for runtime reconciliation.",
        )

    with pytest.raises(
        ValueError,
        match="balance confirmation support_ref must be blank for manual_assertion",
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="manual_assertion",
            support_ref="note.txt",
            asserted_meaning="Operator asserts the runtime balance directly.",
            reviewed_by="operator",
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
        )

    confirmation = BalanceConfirmation(
        source=SourceId("fixture"),
        location_id=LocationId("taxable:spot"),
        instrument_id=InstrumentId("symbol:BTC"),
        quantity=Decimal("1"),
        as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
        as_of_precision=TemporalPrecision.TIMESTAMP,
        confirmation_kind="external_support",
        support_ref="statement.pdf#page=1",
        asserted_meaning="Closing balance from the cited statement.",
        reviewed_by="operator",
        reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
        reason="Needed for runtime reconciliation.",
    )

    assert confirmation.as_of_at.tzinfo is UTC
    assert confirmation.reviewed_at is not None
    assert confirmation.reviewed_at.tzinfo is UTC


def test_balance_confirmation_rejects_blank_required_fields() -> None:
    with pytest.raises(
        ValueError, match="balance confirmation instrument_id must not be blank"
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId(""),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="manual_assertion",
            asserted_meaning="Operator asserts the runtime balance directly.",
            reviewed_by="operator",
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
        )

    with pytest.raises(
        ValueError,
        match="balance confirmation confirmation_kind must be one of:",
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="unsupported_kind",
            asserted_meaning="Operator asserts the runtime balance directly.",
            reviewed_by="operator",
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
        )

    with pytest.raises(
        ValueError,
        match="balance confirmation asserted_meaning must not be blank",
    ):
        BalanceConfirmation(
            source=SourceId("fixture"),
            location_id=LocationId("taxable:spot"),
            instrument_id=InstrumentId("symbol:BTC"),
            quantity=Decimal("1"),
            as_of_at=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
            as_of_precision=TemporalPrecision.TIMESTAMP,
            confirmation_kind="manual_assertion",
            asserted_meaning=" ",
            reviewed_by="operator",
            reviewed_at=datetime(2025, 1, 2, 0, 0, 0, tzinfo=UTC),
            reason="Needed for runtime reconciliation.",
        )
