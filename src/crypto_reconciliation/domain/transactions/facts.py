"""Provider-neutral transaction fact models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp

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

    @property
    def asset_in(self) -> AssetSymbol | None:
        leg = next((candidate for candidate in self.legs if candidate.direction == "in"), None)
        return None if leg is None else leg.asset

    @property
    def amount_in(self) -> Decimal | None:
        leg = next((candidate for candidate in self.legs if candidate.direction == "in"), None)
        return None if leg is None else leg.amount

    @property
    def asset_out(self) -> AssetSymbol | None:
        leg = next((candidate for candidate in self.legs if candidate.direction == "out"), None)
        return None if leg is None else leg.asset

    @property
    def amount_out(self) -> Decimal | None:
        leg = next((candidate for candidate in self.legs if candidate.direction == "out"), None)
        return None if leg is None else leg.amount

    @property
    def fee_asset(self) -> AssetSymbol | None:
        leg = self.fee_legs[0] if self.fee_legs else None
        return None if leg is None else leg.asset

    @property
    def fee_amount(self) -> Decimal | None:
        leg = self.fee_legs[0] if self.fee_legs else None
        return None if leg is None else leg.amount

    @property
    def category(self) -> str:
        if self.projection_type is None:
            return self.economic_kind.value
        return {
            ProjectionType.DEPOSIT: "deposit",
            ProjectionType.DERIVATIVES_FUTURES_LOSS: "derivatives_loss",
            ProjectionType.DERIVATIVES_FUTURES_PROFIT: "derivatives_profit",
            ProjectionType.EXPENSE_NON_TAXABLE: "expense",
            ProjectionType.INTEREST_INCOME: "interest_income",
            ProjectionType.REWARD_BONUS: "reward",
            ProjectionType.STAKING: "staking_reward",
            ProjectionType.SWAP_NON_TAXABLE: "swap",
            ProjectionType.TRADE: "trade",
            ProjectionType.WITHDRAWAL: "withdrawal",
        }[self.projection_type]

    def to_row(self) -> dict[str, str]:
        return {
            "fact_id": str(self.fact_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "timestamp": format_timestamp(self.timestamp),
            "account": self.account,
            "wallet": self.wallet,
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
