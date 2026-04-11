from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.balances import (
    BalanceAssertionStatus,
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
    assert_balance_targets,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId

_AS_OF = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)


def _target(instrument_id: str) -> BalanceTarget:
    return BalanceTarget(
        source=SourceId("coinbase"),
        location_id=LocationId("coinbase"),
        instrument_id=InstrumentId(instrument_id),
        balance_kind="available",
        target_at=_AS_OF,
        target_precision=TemporalPrecision.TIMESTAMP,
    )


def test_assert_balance_targets_marks_exact_matches() -> None:
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
            ),
        ),
    )

    assert result.issues == ()
    assert result.assertions[0].status is BalanceAssertionStatus.MATCHED
    assert (
        result.assertions[0].selected_reference_kind
        is BalanceReferenceKind.SOURCE_DOCUMENT
    )
    assert result.assertions[0].difference == Decimal("0")
    assert result.assertions[0].to_row()["support_ref"] == "statement.pdf#page=1"


def test_assert_balance_targets_emits_drift_and_missing_issues() -> None:
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.0"),
                snapshot_basis="fact_cutoff",
            ),
            BalanceSnapshot(
                target=_target("ETH"),
                quantity=Decimal("2.0"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.5"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
            ),
            BalanceReference(
                target=_target("SOL"),
                quantity=Decimal("3.0"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
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


def test_assert_balance_targets_accepts_observation_gap() -> None:
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.NETWORK_API,
                observed_at=datetime(2025, 12, 31, tzinfo=UTC),
                observed_precision=TemporalPrecision.DATE,
                provider_family="evm_json_rpc",
                provider_block_ref="block:1",
            ),
        ),
    )

    assert result.assertions[0].status is BalanceAssertionStatus.MATCHED
    assert result.assertions[0].observation_gap == "86399"
    assert result.issues == ()


def test_assert_balance_targets_surfaces_duplicate_snapshots() -> None:
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("2"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
            ),
        ),
    )

    assert result.assertions[0].status is BalanceAssertionStatus.MATCHED
    assert [issue.kind for issue in result.issues] == ["duplicate_balance_snapshot"]
    assert [issue.issue_id for issue in result.issues] == [
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:1"
    ]


def test_assert_balance_targets_assigns_distinct_duplicate_issue_ids() -> None:
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1"),
                snapshot_basis="fact_cutoff",
            ),
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("2"),
                snapshot_basis="fact_cutoff",
            ),
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("3"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(),
    )

    assert [issue.issue_id for issue in result.issues] == [
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:1",
        "coinbase:coinbase:BTC:available:duplicate_balance_snapshot:2",
        "coinbase:coinbase:BTC:available:balance_missing_reference",
    ]


def test_assert_balance_targets_uses_operator_assertion_when_it_is_only_reference() -> (
    None
):
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        ),
    )

    assert result.issues == ()
    assert (
        result.assertions[0].selected_reference_kind
        is BalanceReferenceKind.OPERATOR_ASSERTION
    )
    assert result.assertions[0].to_row()["support_ref"] == "statement.pdf#page=1"


def test_assert_balance_targets_prefers_source_document_over_operator_assertion() -> (
    None
):
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.SOURCE_DOCUMENT,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                support_ref="statement.pdf#page=1",
            ),
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("9.0"),
                reference_kind=BalanceReferenceKind.OPERATOR_ASSERTION,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                reviewed_by="operator@example.com",
                reviewed_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ),
        ),
    )

    assert (
        result.assertions[0].selected_reference_kind
        is BalanceReferenceKind.SOURCE_DOCUMENT
    )
    assert result.assertions[0].difference == Decimal("0")


def test_assert_balance_targets_surfaces_conflicting_same_precedence_references() -> (
    None
):
    result = assert_balance_targets(
        snapshots=(
            BalanceSnapshot(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                snapshot_basis="fact_cutoff",
            ),
        ),
        references=(
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.NETWORK_API,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                provider_family="evm_json_rpc",
                provider_block_ref="block:1",
            ),
            BalanceReference(
                target=_target("BTC"),
                quantity=Decimal("1.25"),
                reference_kind=BalanceReferenceKind.NETWORK_API,
                observed_at=_AS_OF,
                observed_precision=TemporalPrecision.TIMESTAMP,
                provider_family="evm_json_rpc",
                provider_block_ref="block:2",
            ),
        ),
    )

    assert result.assertions[0].status is BalanceAssertionStatus.REFERENCE_CONFLICT
    assert result.assertions[0].selected_reference_kind is None
    assert result.assertions[0].reference_quantity is None
    assert result.assertions[0].to_row()["status"] == "reference_conflict"
    assert result.assertions[0].to_row()["selected_reference_kind"] == ""
    assert [issue.kind for issue in result.issues] == [
        "conflicting_balance_references",
        "balance_reference_conflict",
    ]
