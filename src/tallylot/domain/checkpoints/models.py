"""Balance evidence and derived balance state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.types import AssetSymbol, SourceId
from tallylot.domain.value_objects import format_decimal, format_timestamp


@dataclass(frozen=True)
class BalanceEvidence:
    source: SourceId
    account: str
    wallet: str
    asset: AssetSymbol
    quantity: Decimal
    as_of: datetime
    balance_kind: str = "available"
    evidence_ref: str = ""
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "account": self.account,
            "wallet": self.wallet,
            "asset": str(self.asset),
            "quantity": format_decimal(self.quantity),
            "as_of": format_timestamp(self.as_of),
            "balance_kind": self.balance_kind,
            "evidence_ref": self.evidence_ref,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BalanceSnapshot:
    source: SourceId
    account: str
    wallet: str
    asset: AssetSymbol
    quantity: Decimal
    as_of: datetime
    balance_kind: str = "available"
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "account": self.account,
            "wallet": self.wallet,
            "asset": str(self.asset),
            "quantity": format_decimal(self.quantity),
            "as_of": format_timestamp(self.as_of),
            "balance_kind": self.balance_kind,
            "notes": self.notes,
        }
