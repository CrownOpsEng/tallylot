"""Contracts for the manual balance submission checkpoint workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.temporal import TemporalPrecision


@dataclass(frozen=True)
class BalanceSubmissionIssue:
    file_name: str
    row_number: str
    column_name: str
    issue_kind: str
    message: str

    def to_row(self) -> dict[str, str]:
        return {
            "file_name": self.file_name,
            "row_number": self.row_number,
            "column_name": self.column_name,
            "issue_kind": self.issue_kind,
            "message": self.message,
        }


@dataclass(frozen=True)
class BalanceSubmissionRow:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str
    notes: str


@dataclass(frozen=True)
class SubmittedBalanceEvidenceRow:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str
    evidence_ref: str
    notes: str


@dataclass(frozen=True)
class LocationInventorySubmissionRow:
    source: str
    account: str
    wallet: str
    identifier_kind: str
    identifier_value: str
    network_scope: str
    controller: str
    confidence: str
    notes: str


@dataclass(frozen=True)
class BalanceSubmissionValidationResult:
    balance_rows: tuple[BalanceSubmissionRow, ...]
    balance_evidence_rows: tuple[SubmittedBalanceEvidenceRow, ...]
    location_inventory_rows: tuple[LocationInventorySubmissionRow, ...]
    issues: tuple[BalanceSubmissionIssue, ...]
