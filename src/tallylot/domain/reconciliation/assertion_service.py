"""Balance assertion issue assembly."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import LocationId, SourceId

from .assertion_formatting import format_assertion_temporal_text
from .assertion_models import (
    BalanceAssertion,
    BalanceAssertionResult,
    BalanceAssertionStatus,
)
from .confirmation import BalanceConfirmation
from .evidence import BalanceEvidence


@dataclass(frozen=True)
class _SelectedReference:
    record: BalanceEvidence | BalanceConfirmation
    reference_basis: str


@dataclass(frozen=True, order=True)
class _BalanceAssertionKey:
    source: str
    location_id: str
    instrument_id: str
    balance_kind: str


def assert_balance_snapshots(
    snapshots: tuple[BalanceSnapshot, ...],
    evidence: tuple[BalanceEvidence, ...],
    confirmations: tuple[BalanceConfirmation, ...] = (),
) -> BalanceAssertionResult:
    """Compare derived balance snapshots against source-backed balance evidence."""

    snapshots_by_key, snapshot_issues = _index_snapshots(snapshots)
    evidence_by_key, evidence_issues = _index_evidence(evidence)
    confirmation_by_key, confirmation_issues = _index_confirmations(confirmations)
    assertions: list[BalanceAssertion] = []
    issues: list[IssueRecord] = [
        *snapshot_issues,
        *evidence_issues,
        *confirmation_issues,
    ]
    for key in sorted(
        set(snapshots_by_key) | set(evidence_by_key) | set(confirmation_by_key)
    ):
        snapshot = snapshots_by_key.get(key)
        reference = _selected_reference(
            evidence_by_key.get(key),
            confirmation_by_key.get(key),
        )
        assertion = _build_assertion(key, snapshot, reference)
        assertions.append(assertion)
        if assertion.status is not BalanceAssertionStatus.MATCHED:
            issues.append(_issue_for_assertion(assertion))
    return BalanceAssertionResult(
        assertions=tuple(assertions),
        issues=tuple(issues),
    )


def _build_assertion(
    key: _BalanceAssertionKey,
    snapshot: BalanceSnapshot | None,
    reference: _SelectedReference | None,
) -> BalanceAssertion:
    snapshot_quantity = None if snapshot is None else snapshot.quantity
    reference_record = None if reference is None else reference.record
    evidence_quantity = None if reference_record is None else reference_record.quantity
    return BalanceAssertion(
        source=SourceId(key.source),
        location_id=LocationId(key.location_id),
        instrument_id=InstrumentId(key.instrument_id),
        balance_kind=key.balance_kind,
        snapshot_quantity=snapshot_quantity,
        evidence_quantity=evidence_quantity,
        quantity_difference=(snapshot_quantity or Decimal("0"))
        - (evidence_quantity or Decimal("0")),
        status=_assertion_status(snapshot, reference_record),
        reference_basis="" if reference is None else reference.reference_basis,
        snapshot_as_of_at=None if snapshot is None else snapshot.as_of_at,
        snapshot_as_of_precision=(
            None if snapshot is None else snapshot.as_of_precision
        ),
        evidence_as_of_at=None
        if reference_record is None
        else reference_record.as_of_at,
        evidence_as_of_precision=(
            None if reference_record is None else reference_record.as_of_precision
        ),
        evidence_ref=_reference_ref(reference_record),
        notes="" if reference_record is None else reference_record.notes,
    )


def _assertion_status(
    snapshot: BalanceSnapshot | None,
    reference_record: BalanceEvidence | BalanceConfirmation | None,
) -> BalanceAssertionStatus:
    if snapshot is None:
        return BalanceAssertionStatus.MISSING_SNAPSHOT
    if reference_record is None:
        return BalanceAssertionStatus.MISSING_REFERENCE
    if (
        snapshot.as_of_at != reference_record.as_of_at
        or snapshot.as_of_precision != reference_record.as_of_precision
    ):
        return BalanceAssertionStatus.TIMESTAMP_MISMATCH
    if snapshot.quantity != reference_record.quantity:
        return BalanceAssertionStatus.DRIFT
    return BalanceAssertionStatus.MATCHED


def _issue_for_assertion(assertion: BalanceAssertion) -> IssueRecord:
    issue_kind = f"balance_{assertion.status.value}"
    return IssueRecord(
        issue_id=":".join(
            (
                str(assertion.source),
                str(assertion.location_id),
                str(assertion.instrument_id),
                assertion.balance_kind,
                issue_kind,
            )
        ),
        source=str(assertion.source),
        adapter_id="reconciliation",
        severity="high",
        kind=issue_kind,
        message=(
            f"Balance assertion {assertion.status.value} for "
            f"{assertion.location_id} {assertion.instrument_id}."
        ),
        context_timestamp=format_assertion_temporal_text(
            assertion.snapshot_as_of_at or assertion.evidence_as_of_at,
            assertion.snapshot_as_of_precision or assertion.evidence_as_of_precision,
            label="balance assertion issue timestamp",
        ),
        raw_file=assertion.evidence_ref,
    )


def _snapshot_key(snapshot: BalanceSnapshot) -> _BalanceAssertionKey:
    return _BalanceAssertionKey(
        source=str(snapshot.source),
        location_id=str(snapshot.location_id),
        instrument_id=str(snapshot.instrument_id),
        balance_kind=snapshot.balance_kind,
    )


def _evidence_key(record: BalanceEvidence) -> _BalanceAssertionKey:
    return _BalanceAssertionKey(
        source=str(record.source),
        location_id=str(record.location_id),
        instrument_id=str(record.instrument_id),
        balance_kind=record.balance_kind,
    )


def _confirmation_key(record: BalanceConfirmation) -> _BalanceAssertionKey:
    return _BalanceAssertionKey(
        source=str(record.source),
        location_id=str(record.location_id),
        instrument_id=str(record.instrument_id),
        balance_kind=record.balance_kind,
    )


def _index_snapshots(
    snapshots: tuple[BalanceSnapshot, ...],
) -> tuple[dict[_BalanceAssertionKey, BalanceSnapshot], tuple[IssueRecord, ...]]:
    snapshots_by_key: dict[_BalanceAssertionKey, BalanceSnapshot] = {}
    duplicate_counts: dict[_BalanceAssertionKey, int] = {}
    issues: list[IssueRecord] = []
    for snapshot in snapshots:
        key = _snapshot_key(snapshot)
        if key in snapshots_by_key:
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
            issues.append(
                _duplicate_input_issue(
                    key,
                    kind="duplicate_balance_snapshot",
                    duplicate_index=duplicate_counts[key],
                    context_timestamp=format_assertion_temporal_text(
                        snapshot.as_of_at,
                        snapshot.as_of_precision,
                        label="duplicate balance issue timestamp",
                    ),
                )
            )
            continue
        snapshots_by_key[key] = snapshot
    return snapshots_by_key, tuple(issues)


def _index_evidence(
    evidence: tuple[BalanceEvidence, ...],
) -> tuple[dict[_BalanceAssertionKey, BalanceEvidence], tuple[IssueRecord, ...]]:
    evidence_by_key: dict[_BalanceAssertionKey, BalanceEvidence] = {}
    duplicate_counts: dict[_BalanceAssertionKey, int] = {}
    issues: list[IssueRecord] = []
    for record in evidence:
        key = _evidence_key(record)
        if key in evidence_by_key:
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
            issues.append(
                _duplicate_input_issue(
                    key,
                    kind="duplicate_balance_evidence",
                    duplicate_index=duplicate_counts[key],
                    context_timestamp=format_assertion_temporal_text(
                        record.as_of_at,
                        record.as_of_precision,
                        label="duplicate balance issue timestamp",
                    ),
                    raw_file=record.provenance.to_reference_ref(),
                )
            )
            continue
        evidence_by_key[key] = record
    return evidence_by_key, tuple(issues)


def _index_confirmations(
    confirmations: tuple[BalanceConfirmation, ...],
) -> tuple[dict[_BalanceAssertionKey, BalanceConfirmation], tuple[IssueRecord, ...]]:
    confirmation_by_key: dict[_BalanceAssertionKey, BalanceConfirmation] = {}
    duplicate_counts: dict[_BalanceAssertionKey, int] = {}
    issues: list[IssueRecord] = []
    for record in confirmations:
        key = _confirmation_key(record)
        if key in confirmation_by_key:
            duplicate_counts[key] = duplicate_counts.get(key, 0) + 1
            issues.append(
                _duplicate_input_issue(
                    key,
                    kind="duplicate_balance_confirmation",
                    duplicate_index=duplicate_counts[key],
                    context_timestamp=format_assertion_temporal_text(
                        record.as_of_at,
                        record.as_of_precision,
                        label="duplicate balance issue timestamp",
                    ),
                    raw_file=record.support_ref,
                )
            )
            continue
        confirmation_by_key[key] = record
    return confirmation_by_key, tuple(issues)


def _selected_reference(
    evidence_record: BalanceEvidence | None,
    confirmation_record: BalanceConfirmation | None,
) -> _SelectedReference | None:
    if evidence_record is not None:
        return _SelectedReference(
            record=evidence_record,
            reference_basis="source_backed_evidence",
        )
    if confirmation_record is not None:
        return _SelectedReference(
            record=confirmation_record,
            reference_basis="operator_confirmation",
        )
    return None


def _reference_ref(
    record: BalanceEvidence | BalanceConfirmation | None,
) -> str:
    if record is None:
        return ""
    if isinstance(record, BalanceEvidence):
        return record.provenance.to_reference_ref()
    return record.support_ref


def _duplicate_input_issue(
    key: _BalanceAssertionKey,
    *,
    kind: str,
    duplicate_index: int,
    context_timestamp: str,
    raw_file: str = "",
) -> IssueRecord:
    return IssueRecord(
        issue_id=":".join(
            (
                key.source,
                key.location_id,
                key.instrument_id,
                key.balance_kind,
                kind,
                str(duplicate_index),
            )
        ),
        source=key.source,
        adapter_id="reconciliation",
        severity="high",
        kind=kind,
        message=(
            f"Duplicate {key.balance_kind} balance input for "
            f"{key.location_id} {key.instrument_id}."
        ),
        context_timestamp=context_timestamp,
        raw_file=raw_file,
    )
