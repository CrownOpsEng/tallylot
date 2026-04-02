"""Source-backed balance evidence models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.types import AssetSymbol, LocationId, SourceId
from tallylot.domain.value_objects import format_decimal, format_timestamp, require_utc_datetime


@dataclass(frozen=True)
class BalanceEvidence:
    source: SourceId
    location_id: LocationId
    asset: AssetSymbol
    quantity: Decimal
    as_of: datetime
    balance_kind: str = "available"
    evidence_ref: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="balance evidence as_of"),
        )

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "location_id": str(self.location_id),
            "asset": str(self.asset),
            "quantity": format_decimal(self.quantity),
            "as_of": format_timestamp(self.as_of),
            "balance_kind": self.balance_kind,
            "evidence_ref": self.evidence_ref,
            "notes": self.notes,
        }
