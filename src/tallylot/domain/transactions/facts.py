"""Provider-neutral transaction fact models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.domain.value_objects import format_decimal, format_timestamp

from .classification import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode

FactDirection = Literal["in", "out"]


@dataclass(frozen=True)
class FactLegPolicy:
    max_in_legs: int = 1
    max_out_legs: int = 1
    max_fee_legs: int = 1

    def __post_init__(self) -> None:
        if self.max_in_legs < 0:
            raise ValueError("fact leg policy max_in_legs must be non-negative")
        if self.max_out_legs < 0:
            raise ValueError("fact leg policy max_out_legs must be non-negative")
        if self.max_fee_legs < 0:
            raise ValueError("fact leg policy max_fee_legs must be non-negative")
        if self.max_in_legs == 0 and self.max_out_legs == 0:
            raise ValueError("fact leg policy must allow at least one economic leg")


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
    leg_policy: FactLegPolicy = field(default_factory=FactLegPolicy)
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
        inbound_legs = sum(1 for leg in self.legs if leg.direction == "in")
        outbound_legs = sum(1 for leg in self.legs if leg.direction == "out")
        if inbound_legs > self.leg_policy.max_in_legs:
            raise ValueError("transaction fact inbound legs exceed declared leg policy")
        if outbound_legs > self.leg_policy.max_out_legs:
            raise ValueError("transaction fact outbound legs exceed declared leg policy")
        if len(self.fee_legs) > self.leg_policy.max_fee_legs:
            raise ValueError("transaction fact fee legs exceed declared leg policy")

    @property
    def economic_kind(self) -> EconomicKind:
        return self.classification.economic_kind

    @property
    def journal_intent(self) -> JournalIntent:
        return self.classification.journal_intent

    @property
    def tax_treatment_code(self) -> TaxTreatmentCode:
        return self.classification.tax_treatment_code

    @property
    def projection_type(self) -> ProjectionType | None:
        return self.classification.projection_type

    def to_row(self) -> dict[str, str]:
        return {
            "fact_id": str(self.fact_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "timestamp": format_timestamp(self.timestamp),
            "account": self.account,
            "wallet": self.wallet,
            "max_in_legs": str(self.leg_policy.max_in_legs),
            "max_out_legs": str(self.leg_policy.max_out_legs),
            "max_fee_legs": str(self.leg_policy.max_fee_legs),
            "economic_kind": self.economic_kind.value,
            "projection_type": "" if self.projection_type is None else self.projection_type.value,
            "journal_intent": self.journal_intent.value,
            "tax_treatment_code": self.tax_treatment_code.value,
            "description": self.description,
            "provider_operation_key": self.provider_operation_key,
            "operation_group_id": self.operation_group_id,
            "tx_hash": self.tx_hash or "",
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "confidence": self.confidence,
            "status": self.status,
            "legs": "|".join(
                f"{leg.direction}:{leg.asset}:{format_decimal(leg.amount)}:{leg.account}:{leg.wallet}"
                for leg in self.legs
            ),
            "fee_legs": "|".join(
                f"{leg.direction}:{leg.asset}:{format_decimal(leg.amount)}:{leg.account}:{leg.wallet}"
                for leg in self.fee_legs
            ),
        }
