"""Operator-confirmed balance reference models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.checkpoints.balance_kinds import normalize_balance_kind
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    format_timestamp,
    require_temporal_datetime,
    require_utc_datetime,
)

_CONFIRMATION_KINDS = frozenset({"external_support", "manual_assertion"})


def normalize_balance_confirmation_kind(value: str) -> str:
    normalized = value.strip()
    if normalized not in _CONFIRMATION_KINDS:
        expected = ", ".join(sorted(_CONFIRMATION_KINDS))
        raise ValueError(
            f"balance confirmation confirmation_kind must be one of: {expected}"
        )
    return normalized


@dataclass(frozen=True)
class BalanceConfirmation:
    source: SourceId
    location_id: LocationId
    instrument_id: InstrumentId
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str = "available"
    confirmation_kind: str = "manual_assertion"
    support_ref: str = ""
    asserted_meaning: str = ""
    reviewed_by: str = ""
    reviewed_at: datetime | None = None
    reason: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("balance confirmation instrument_id must not be blank")
        asserted_meaning = self.asserted_meaning.strip()
        if not asserted_meaning:
            raise ValueError("balance confirmation asserted_meaning must not be blank")
        reviewed_by = self.reviewed_by.strip()
        if not reviewed_by:
            raise ValueError("balance confirmation reviewed_by must not be blank")
        reason = self.reason.strip()
        if not reason:
            raise ValueError("balance confirmation reason must not be blank")
        reviewed_at = self.reviewed_at
        if reviewed_at is None:
            raise ValueError("balance confirmation reviewed_at must not be blank")
        confirmation_kind = normalize_balance_confirmation_kind(self.confirmation_kind)
        support_ref = self.support_ref.strip()
        if confirmation_kind == "external_support" and not support_ref:
            raise ValueError(
                "balance confirmation support_ref is required for external_support"
            )
        if confirmation_kind == "manual_assertion" and support_ref:
            raise ValueError(
                "balance confirmation support_ref must be blank for manual_assertion"
            )
        object.__setattr__(
            self,
            "balance_kind",
            normalize_balance_kind(self.balance_kind),
        )
        object.__setattr__(self, "confirmation_kind", confirmation_kind)
        object.__setattr__(self, "support_ref", support_ref)
        object.__setattr__(self, "asserted_meaning", asserted_meaning)
        object.__setattr__(self, "reviewed_by", reviewed_by)
        object.__setattr__(
            self,
            "reviewed_at",
            require_utc_datetime(
                reviewed_at,
                label="balance confirmation reviewed_at",
            ),
        )
        object.__setattr__(self, "reason", reason)
        object.__setattr__(
            self,
            "as_of_at",
            require_temporal_datetime(
                self.as_of_at,
                precision=self.as_of_precision,
                label="balance confirmation as_of_at",
            ),
        )

    def to_row(self) -> dict[str, str]:
        reviewed_at = self.reviewed_at
        if reviewed_at is None:
            raise ValueError("balance confirmation reviewed_at must not be blank")
        return {
            "source": str(self.source),
            "location_id": str(self.location_id),
            "instrument_id": str(self.instrument_id),
            "quantity": format_decimal(self.quantity),
            "as_of_at": format_temporal_value(
                self.as_of_at,
                precision=self.as_of_precision,
                label="balance confirmation as_of_at",
            ),
            "as_of_precision": self.as_of_precision.value,
            "balance_kind": self.balance_kind,
            "confirmation_kind": self.confirmation_kind,
            "support_ref": self.support_ref,
            "asserted_meaning": self.asserted_meaning,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": format_timestamp(reviewed_at),
            "reason": self.reason,
            "notes": self.notes,
        }
