"""Derived balance state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    require_temporal_datetime,
)


@dataclass(frozen=True)
class BalanceSnapshot:
    source: SourceId
    location_id: LocationId
    instrument_id: InstrumentId
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str = "available"
    notes: str = ""

    def __post_init__(self) -> None:
        if not str(self.instrument_id):
            raise ValueError("balance snapshot instrument_id must not be blank")
        object.__setattr__(
            self,
            "as_of_at",
            require_temporal_datetime(
                self.as_of_at,
                precision=self.as_of_precision,
                label="balance snapshot as_of_at",
            ),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "location_id": str(self.location_id),
            "instrument_id": str(self.instrument_id),
            "quantity": format_decimal(self.quantity),
            "as_of_at": format_temporal_value(
                self.as_of_at,
                precision=self.as_of_precision,
                label="balance snapshot as_of_at",
            ),
            "as_of_precision": self.as_of_precision.value,
            "balance_kind": self.balance_kind,
            "notes": self.notes,
        }
