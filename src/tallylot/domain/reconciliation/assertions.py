"""Balance assertion models and issue assembly."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    require_temporal_datetime,
)

from .evidence import BalanceEvidence


class BalanceAssertionStatus(StrEnum):
    """Comparison status for one derived snapshot versus one evidence row."""

    MATCHED = "matched"
    DRIFT = "drift"
    MISSING_SNAPSHOT = "missing_snapshot"
    MISSING_EVIDENCE = "missing_evidence"
    TIMESTAMP_MISMATCH = "timestamp_mismatch"


@dataclass(frozen=True)
class BalanceAssertion:
    """Comparison row for one source, location, instrument, and balance kind."""

    source: SourceId
    location_id: LocationId
    instrument_id: InstrumentId
    balance_kind: str
    snapshot_quantity: Decimal | None
    evidence_quantity: Decimal | None
    quantity_difference: Decimal
    status: BalanceAssertionStatus
    snapshot_as_of_at: datetime | None = None
    snapshot_as_of_precision: TemporalPrecision | None = None
    evidence_as_of_at: datetime | None = None
    evidence_as_of_precision: TemporalPrecision | None = None
    evidence_ref: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("balance assertion instrument_id must not be blank")
        if not self.balance_kind:
            raise ValueError("balance assertion balance_kind must not be blank")
        object.__setattr__(
            self,
            "snapshot_as_of_at",
            _normalized_temporal_value(
                self.snapshot_as_of_at,
                self.snapshot_as_of_precision,
                label="balance assertion snapshot_as_of_at",
            ),
        )
        object.__setattr__(
            self,
            "evidence_as_of_at",
            _normalized_temporal_value(
                self.evidence_as_of_at,
                self.evidence_as_of_precision,
                label="balance assertion evidence_as_of_at",
            ),
        )

    def to_row(self) -> dict[str, str]:
        """Render the assertion as a deterministic CSV row."""

        return {
            "source": str(self.source),
            "location_id": str(self.location_id),
            "instrument_id": str(self.instrument_id),
            "balance_kind": self.balance_kind,
            "snapshot_quantity": format_decimal(self.snapshot_quantity),
            "evidence_quantity": format_decimal(self.evidence_quantity),
            "quantity_difference": format_decimal(self.quantity_difference),
            "status": self.status.value,
            "snapshot_as_of_at": _temporal_text(
                self.snapshot_as_of_at,
                self.snapshot_as_of_precision,
                label="balance assertion snapshot_as_of_at",
            ),
            "snapshot_as_of_precision": _precision_text(self.snapshot_as_of_precision),
            "evidence_as_of_at": _temporal_text(
                self.evidence_as_of_at,
                self.evidence_as_of_precision,
                label="balance assertion evidence_as_of_at",
            ),
            "evidence_as_of_precision": _precision_text(self.evidence_as_of_precision),
            "evidence_ref": self.evidence_ref,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BalanceAssertionResult:
    """Balance assertion output rows and explicit reconciliation issues."""

    assertions: tuple[BalanceAssertion, ...]
    issues: tuple[IssueRecord, ...]


@dataclass(frozen=True, order=True)
class _BalanceAssertionKey:
    source: str
    location_id: str
    instrument_id: str
    balance_kind: str


def assert_balance_snapshots(
    snapshots: tuple[BalanceSnapshot, ...],
    evidence: tuple[BalanceEvidence, ...],
) -> BalanceAssertionResult:
    """Compare derived balance snapshots against source-backed balance evidence."""

    snapshots_by_key, snapshot_issues = _index_snapshots(snapshots)
    evidence_by_key, evidence_issues = _index_evidence(evidence)
    assertions: list[BalanceAssertion] = []
    issues: list[IssueRecord] = [*snapshot_issues, *evidence_issues]
    for key in sorted(set(snapshots_by_key) | set(evidence_by_key)):
        snapshot = snapshots_by_key.get(key)
        evidence_record = evidence_by_key.get(key)
        assertion = _build_assertion(key, snapshot, evidence_record)
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
    evidence_record: BalanceEvidence | None,
) -> BalanceAssertion:
    snapshot_quantity = None if snapshot is None else snapshot.quantity
    evidence_quantity = None if evidence_record is None else evidence_record.quantity
    return BalanceAssertion(
        source=SourceId(key.source),
        location_id=LocationId(key.location_id),
        instrument_id=InstrumentId(key.instrument_id),
        balance_kind=key.balance_kind,
        snapshot_quantity=snapshot_quantity,
        evidence_quantity=evidence_quantity,
        quantity_difference=(snapshot_quantity or Decimal("0"))
        - (evidence_quantity or Decimal("0")),
        status=_assertion_status(snapshot, evidence_record),
        snapshot_as_of_at=None if snapshot is None else snapshot.as_of_at,
        snapshot_as_of_precision=(
            None if snapshot is None else snapshot.as_of_precision
        ),
        evidence_as_of_at=None if evidence_record is None else evidence_record.as_of_at,
        evidence_as_of_precision=(
            None if evidence_record is None else evidence_record.as_of_precision
        ),
        evidence_ref="" if evidence_record is None else evidence_record.evidence_ref,
        notes="" if evidence_record is None else evidence_record.notes,
    )


def _assertion_status(
    snapshot: BalanceSnapshot | None,
    evidence_record: BalanceEvidence | None,
) -> BalanceAssertionStatus:
    if snapshot is None:
        return BalanceAssertionStatus.MISSING_SNAPSHOT
    if evidence_record is None:
        return BalanceAssertionStatus.MISSING_EVIDENCE
    if (
        snapshot.as_of_at != evidence_record.as_of_at
        or snapshot.as_of_precision != evidence_record.as_of_precision
    ):
        return BalanceAssertionStatus.TIMESTAMP_MISMATCH
    if snapshot.quantity != evidence_record.quantity:
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
        context_timestamp=_temporal_text(
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
                    context_timestamp=_temporal_text(
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
                    context_timestamp=_temporal_text(
                        record.as_of_at,
                        record.as_of_precision,
                        label="duplicate balance issue timestamp",
                    ),
                    raw_file=record.evidence_ref,
                )
            )
            continue
        evidence_by_key[key] = record
    return evidence_by_key, tuple(issues)


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


def _normalized_temporal_value(
    value: datetime | None,
    precision: TemporalPrecision | None,
    *,
    label: str,
) -> datetime | None:
    if value is None:
        if precision is not None:
            raise ValueError(f"{label} requires a matching precision when present")
        return None
    if precision is None:
        raise ValueError(f"{label} requires a matching precision when present")
    return require_temporal_datetime(value, precision=precision, label=label)


def _temporal_text(
    value: datetime | None,
    precision: TemporalPrecision | None,
    *,
    label: str,
) -> str:
    if value is None or precision is None:
        return ""
    return format_temporal_value(value, precision=precision, label=label)


def _precision_text(precision: TemporalPrecision | None) -> str:
    return "" if precision is None else precision.value
