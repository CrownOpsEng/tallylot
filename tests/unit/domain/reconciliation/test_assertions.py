from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import (
    BalanceAssertion,
    BalanceAssertionStatus,
    BalanceConfirmation,
    BalanceEvidence,
    assert_balance_snapshots,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId

_AS_OF = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


def test_assert_balance_snapshots_marks_exact_matches() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
    )

    assert result.issues == ()
    assert result.assertions[0].status is BalanceAssertionStatus.MATCHED
    assert result.assertions[0].reference_basis == "source_backed_evidence"
    assert result.assertions[0].quantity_difference == Decimal("0")
    assert result.assertions[0].to_row()["evidence_ref"] == "statement.pdf#page=1"


def test_assert_balance_snapshots_emits_drift_and_missing_issues() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.0"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("ETH"),
                quantity=Decimal("2.0"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.5"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("SOL"),
                quantity=Decimal("3.0"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
    )

    assert [assertion.status for assertion in result.assertions] == [
        BalanceAssertionStatus.DRIFT,
        BalanceAssertionStatus.MISSING_REFERENCE,
        BalanceAssertionStatus.MISSING_SNAPSHOT,
    ]
    assert [issue.kind for issue in result.issues] == [
        "balance_drift",
        "balance_missing_reference",
        "balance_missing_snapshot",
    ]


def test_assert_balance_snapshots_flags_timestamp_mismatch() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=datetime(2026, 1, 1, tzinfo=UTC),
                as_of_precision=TemporalPrecision.DATE,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
    )

    assert result.assertions[0].status is BalanceAssertionStatus.TIMESTAMP_MISMATCH
    assert result.assertions[0].quantity_difference == Decimal("0")
    assert result.issues[0].kind == "balance_timestamp_mismatch"


def test_assert_balance_snapshots_surfaces_duplicate_inputs() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("2"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
    )

    assert result.assertions[0].status is BalanceAssertionStatus.MATCHED
    assert [issue.kind for issue in result.issues] == ["duplicate_balance_snapshot"]
    assert [issue.issue_id for issue in result.issues] == [
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:1"
    ]


def test_assert_balance_snapshots_assigns_distinct_duplicate_issue_ids() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("2"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("3"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(),
    )

    assert [issue.issue_id for issue in result.issues] == [
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:1",
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:2",
        "coinbase:coinbase:BTC:available:balance_missing_reference",
    ]


def test_assert_balance_snapshots_uses_confirmation_when_evidence_is_absent() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(),
        confirmations=(
            BalanceConfirmation(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                confirmation_kind="external_support",
                support_ref="statement.pdf#page=1",
                asserted_meaning="Closing balance from the cited statement.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    assert result.issues == ()
    assert result.assertions[0].reference_basis == "operator_confirmation"
    assert result.assertions[0].to_row()["evidence_ref"] == "statement.pdf#page=1"


def test_assert_balance_snapshots_prefers_evidence_over_confirmation() -> None:
    result = assert_balance_snapshots(
        snapshots=(
            BalanceSnapshot(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
            ),
        ),
        evidence=(
            BalanceEvidence(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("1.25"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
            ),
        ),
        confirmations=(
            BalanceConfirmation(
                source=SourceId("coinbase"),
                location_id=LocationId("coinbase"),
                instrument_id=InstrumentId("BTC"),
                quantity=Decimal("9.99"),
                as_of_at=_AS_OF,
                as_of_precision=TemporalPrecision.TIMESTAMP,
                confirmation_kind="manual_assertion",
                asserted_meaning="Operator asserted a conflicting balance.",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                reason="Needed for runtime reconciliation.",
            ),
        ),
    )

    assert result.issues == ()
    assert result.assertions[0].reference_basis == "source_backed_evidence"
    assert result.assertions[0].evidence_quantity == Decimal("1.25")


def test_balance_assertion_requires_valid_temporal_pairs() -> None:
    with pytest.raises(
        ValueError,
        match="balance assertion snapshot_as_of_at requires a matching precision",
    ):
        BalanceAssertion(
            source=SourceId("coinbase"),
            location_id=LocationId("coinbase"),
            instrument_id=InstrumentId("BTC"),
            balance_kind="available",
            snapshot_quantity=Decimal("1"),
            evidence_quantity=Decimal("1"),
            quantity_difference=Decimal("0"),
            status=BalanceAssertionStatus.MATCHED,
            snapshot_as_of_at=_AS_OF,
        )


def test_assertion_and_balance_models_normalize_blank_balance_kinds() -> None:
    snapshot = BalanceSnapshot(
        source=SourceId("coinbase"),
        location_id=LocationId("coinbase"),
        instrument_id=InstrumentId("BTC"),
        quantity=Decimal("1"),
        as_of_at=_AS_OF,
        as_of_precision=TemporalPrecision.TIMESTAMP,
        balance_kind=" ",
    )
    evidence = BalanceEvidence(
        source=SourceId("coinbase"),
        location_id=LocationId("coinbase"),
        instrument_id=InstrumentId("BTC"),
        quantity=Decimal("1"),
        as_of_at=_AS_OF,
        as_of_precision=TemporalPrecision.TIMESTAMP,
        balance_kind="",
        provenance=ProvenanceLocator.from_reference_ref("statement.pdf#page=1"),
    )
    assertion = BalanceAssertion(
        source=SourceId("coinbase"),
        location_id=LocationId("coinbase"),
        instrument_id=InstrumentId("BTC"),
        balance_kind=" locked ",
        snapshot_quantity=Decimal("1"),
        evidence_quantity=Decimal("1"),
        quantity_difference=Decimal("0"),
        status=BalanceAssertionStatus.MATCHED,
    )

    assert snapshot.balance_kind == "available"
    assert evidence.balance_kind == "available"
    assert assertion.balance_kind == "locked"
