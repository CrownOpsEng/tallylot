"""Balance assertion models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from tallylot.domain.checkpoints.balance_kinds import normalize_balance_kind
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.issues import IssueRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    format_decimal,
    require_temporal_datetime,
)

from .assertion_formatting import (
    format_assertion_precision,
    format_assertion_temporal_text,
)


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
        object.__setattr__(
            self,
            "balance_kind",
            normalize_balance_kind(self.balance_kind),
        )
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
            "snapshot_as_of_at": format_assertion_temporal_text(
                self.snapshot_as_of_at,
                self.snapshot_as_of_precision,
                label="balance assertion snapshot_as_of_at",
            ),
            "snapshot_as_of_precision": format_assertion_precision(
                self.snapshot_as_of_precision
            ),
            "evidence_as_of_at": format_assertion_temporal_text(
                self.evidence_as_of_at,
                self.evidence_as_of_precision,
                label="balance assertion evidence_as_of_at",
            ),
            "evidence_as_of_precision": format_assertion_precision(
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
