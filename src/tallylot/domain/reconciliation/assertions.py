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
            "snapshot_as_of_precision": _precision_text(
                self.snapshot_as_of_precision
            ),
            "evidence_as_of_at": _temporal_text(
                self.evidence_as_of_at,
                self.evidence_as_of_precision,
                label="balance assertion evidence_as_of_at",
            ),
            "evidence_as_of_precision": _precision_text(
                self.evidence_as_of_precision
            ),
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

    snapshots_by_key = {
        _snapshot_key(snapshot): snapshot for snapshot in snapshots
    }
    evidence_by_key = {_evidence_key(record): record for record in evidence}
    assertions: list[BalanceAssertion] = []
    issues: list[IssueRecord] = []
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
    return IssueRecord(
        issue_id=":".join(
            (
                str(assertion.source),
                str(assertion.location_id),
                str(assertion.instrument_id),
                assertion.balance_kind,
                assertion.status.value,
            )
        ),
        source=str(assertion.source),
        adapter_id="reconciliation",
        severity="high",
        kind=f"balance_{assertion.status.value}",
        message=(
            f"Balance assertion {assertion.status.value} for "
            f"{assertion.location_id} {assertion.instrument_id}."
        ),
        context_timestamp=_temporal_text(
            assertion.snapshot_as_of_at or assertion.evidence_as_of_at,
            assertion.snapshot_as_of_precision
            or assertion.evidence_as_of_precision,
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
