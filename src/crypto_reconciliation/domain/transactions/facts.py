"""Provider-neutral transaction fact models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId

from .classification import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode

FactDirection = Literal["in", "out"]


@dataclass(frozen=True)
class FactClassification:
    economic_kind: EconomicKind
    journal_intent: JournalIntent
    tax_treatment_code: TaxTreatmentCode
    projection_type: ProjectionType | None = None


@dataclass(frozen=True)
class EconomicLeg:
    direction: FactDirection
    asset: AssetSymbol
    amount: Decimal
    account: str = ""
    wallet: str = ""

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise ValueError("fact leg amount must be greater than zero")


@dataclass(frozen=True)
class TransactionFact:
    fact_id: TransactionId
    source: SourceId
    adapter_id: AdapterId
    timestamp: datetime
    account: str
    wallet: str
    classification: FactClassification
    legs: tuple[EconomicLeg, ...]
    fee_legs: tuple[EconomicLeg, ...] = ()
    description: str = ""
    provider_operation_key: str = ""
    operation_group_id: str = ""
    tx_hash: str | None = None
    raw_file: str = ""
    raw_row_ref: str = ""
    confidence: str = "high"
    status: str = "mapped"

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("transaction fact must include at least one economic leg")
