"""Contracts for the manual balance submission checkpoint workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tallylot.domain.balances import BalanceReferenceKind, normalize_balance_kind
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


class BalanceSnapshotSubmissionRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1)
    account: str = Field(min_length=1)
    wallet: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    quantity: Decimal
    target_at: datetime
    target_precision: TemporalPrecision
    balance_kind: str = "available"
    notes: str = ""

    @field_validator("balance_kind", mode="before")
    @classmethod
    def _normalize_balance_kind(cls, value: object) -> str:
        return normalize_balance_kind("" if value is None else str(value))


class BalanceReferenceSubmissionRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1)
    account: str = Field(min_length=1)
    wallet: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    quantity: Decimal
    target_at: datetime
    target_precision: TemporalPrecision
    balance_kind: str = "available"
    reference_kind: BalanceReferenceKind
    observed_at: datetime
    observed_precision: TemporalPrecision
    support_ref: str = ""
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    notes: str = ""

    @field_validator("balance_kind", mode="before")
    @classmethod
    def _normalize_balance_kind(cls, value: object) -> str:
        return normalize_balance_kind("" if value is None else str(value))


class LocationInventorySubmissionRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    source: str = Field(min_length=1)
    account: str = Field(min_length=1)
    wallet: str = Field(min_length=1)
    identifier_kind: str = Field(min_length=1)
    identifier_value: str = Field(min_length=1)
    network_scope: str = ""
    controller: str = ""
    confidence: str = Field(min_length=1)
    notes: str = ""


@dataclass(frozen=True)
class BalanceSubmissionValidationResult:
    balance_snapshot_rows: tuple[BalanceSnapshotSubmissionRow, ...]
    balance_reference_rows: tuple[BalanceReferenceSubmissionRow, ...]
    location_inventory_rows: tuple[LocationInventorySubmissionRow, ...]
    issues: tuple[BalanceSubmissionIssue, ...]
