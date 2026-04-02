"""Canonical event and balance models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp


@dataclass(frozen=True)
class CanonicalEvent:
    event_id: EventId
    source: SourceId
    adapter_id: AdapterId
    account: str
    wallet: str
    timestamp: datetime
    event_kind: str
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
    render_type: str | None = None
    render_exchange: str | None = None
    render_group: str | None = None
    render_comment: str | None = None
    render_comment_mode: str | None = None
    render_tx_id: str | None = None
    render_tx_id_mode: str | None = None
    render_allowed_types: str | None = None
    render_match_window_seconds: str | None = None
    render_fee_tolerance: str | None = None
    render_notes: str | None = None

    def __post_init__(self) -> None:
        self._validate_amount_pair("asset_in", self.asset_in, "amount_in", self.amount_in)
        self._validate_amount_pair("asset_out", self.asset_out, "amount_out", self.amount_out)
        self._validate_amount_pair("fee_asset", self.fee_asset, "fee_amount", self.fee_amount)
        if self.amount_in is None and self.amount_out is None:
            raise ValueError("canonical event must include an inbound or outbound amount")

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
            raise ValueError(f"canonical event {asset_label} and {amount_label} must both be present")
        if amount <= Decimal("0"):
            raise ValueError(f"canonical event {amount_label} must be greater than zero")

    def to_row(self) -> dict[str, str]:
        return {
            "event_id": str(self.event_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "account": self.account,
            "wallet": self.wallet,
            "timestamp": format_timestamp(self.timestamp),
            "event_kind": self.event_kind,
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
            "render_type": self.render_type or "",
            "render_exchange": self.render_exchange or "",
            "render_group": self.render_group or "",
            "render_comment": self.render_comment or "",
            "render_comment_mode": self.render_comment_mode or "",
            "render_tx_id": self.render_tx_id or "",
            "render_tx_id_mode": self.render_tx_id_mode or "",
            "render_allowed_types": self.render_allowed_types or "",
            "render_match_window_seconds": self.render_match_window_seconds or "",
            "render_fee_tolerance": self.render_fee_tolerance or "",
            "render_notes": self.render_notes or "",
        }


@dataclass(frozen=True)
class CanonicalBalance:
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
