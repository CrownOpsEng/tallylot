"""Normalized transaction and balance models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp

TransactionCategory = Literal[
    "trade",
    "deposit",
    "withdrawal",
    "interest_income",
    "reward",
    "expense",
    "swap",
    "staking_reward",
    "derivatives_profit",
    "derivatives_loss",
]


@dataclass(frozen=True)
class NormalizedTransaction:
    transaction_id: TransactionId
    source: SourceId
    adapter_id: AdapterId
    account: str
    wallet: str
    timestamp: datetime
    category: TransactionCategory
    economic_kind: str = ""
    projection_type: str = ""
    journal_intent: str = ""
    tax_treatment_code: str = ""
    provider_operation_key: str = ""
    group_key: str = ""
    description: str = ""
    asset_in: AssetSymbol | None = None
    amount_in: Decimal | None = None
    asset_out: AssetSymbol | None = None
    amount_out: Decimal | None = None
    fee_asset: AssetSymbol | None = None
    fee_amount: Decimal | None = None
    tx_hash: str | None = None
    raw_file: str = ""
    raw_row_ref: str = ""
    confidence: str = "high"
    status: str = "mapped"

    def __post_init__(self) -> None:
        self._validate_amount_pair("asset_in", self.asset_in, "amount_in", self.amount_in)
        self._validate_amount_pair("asset_out", self.asset_out, "amount_out", self.amount_out)
        self._validate_amount_pair("fee_asset", self.fee_asset, "fee_amount", self.fee_amount)
        if self.amount_in is None and self.amount_out is None:
            raise ValueError("transaction must include an inbound or outbound amount")

    @staticmethod
    def _validate_amount_pair(
        asset_label: str,
        asset: AssetSymbol | None,
        amount_label: str,
        amount: Decimal | None,
    ) -> None:
        if asset is None and amount is None:
            return
        if asset is None or amount is None:
            raise ValueError(f"transaction {asset_label} and {amount_label} must both be present")
        if amount <= Decimal("0"):
            raise ValueError(f"transaction {amount_label} must be greater than zero")

    def to_row(self) -> dict[str, str]:
        return {
            "transaction_id": str(self.transaction_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "account": self.account,
            "wallet": self.wallet,
            "timestamp": format_timestamp(self.timestamp),
            "category": self.category,
            "economic_kind": self.economic_kind,
            "projection_type": self.projection_type,
            "journal_intent": self.journal_intent,
            "tax_treatment_code": self.tax_treatment_code,
            "provider_operation_key": self.provider_operation_key,
            "group_key": self.group_key,
            "description": self.description,
            "asset_in": str(self.asset_in or ""),
            "amount_in": format_decimal(self.amount_in),
            "asset_out": str(self.asset_out or ""),
            "amount_out": format_decimal(self.amount_out),
            "fee_asset": str(self.fee_asset or ""),
            "fee_amount": format_decimal(self.fee_amount),
            "tx_hash": self.tx_hash or "",
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "confidence": self.confidence,
            "status": self.status,
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
