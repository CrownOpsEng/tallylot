"""Core immutable domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from .types import AdapterId, AssetSymbol, EventId, SourceId
from .value_objects import format_decimal, format_timestamp


class AdapterCapability(StrEnum):
    NORMALIZE = "normalize"
    WALLET_INVENTORY = "wallet_inventory"
    OUTPUT_RENDER = "output_render"
    REVIEW = "review"


def _empty_metadata() -> dict[str, str]:
    return {}


def _empty_object_map() -> dict[str, object]:
    return {}


@dataclass(frozen=True)
class AdapterManifest:
    adapter_id: AdapterId
    display_name: str
    version: str
    capabilities: frozenset[AdapterCapability]
    supported: bool = True
    description: str = ""


@dataclass(frozen=True)
class FileInventoryEntry:
    relative_path: str
    suffix: str
    size_bytes: int
    sha256: str
    row_count: int | None = None
    header: tuple[str, ...] = ()
    timestamp_resolution: str = ""
    timezone_mode: str = ""
    timezone_value: str = ""
    timezone_conflict: str = ""


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


@dataclass(frozen=True)
class IssueRecord:
    issue_id: str
    source: str
    adapter_id: str
    severity: str
    kind: str
    message: str
    raw_file: str = ""
    raw_row_ref: str = ""
    status: str = "open"

    def to_row(self) -> dict[str, str]:
        return {
            "issue_id": self.issue_id,
            "source": self.source,
            "adapter_id": self.adapter_id,
            "severity": self.severity,
            "kind": self.kind,
            "message": self.message,
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "status": self.status,
        }


@dataclass(frozen=True)
class NormalizationReviewRecord:
    review_id: str
    source: str
    adapter_id: str
    scope: str
    kind: str
    message: str
    raw_file: str = ""
    raw_row_ref: str = ""
    field_name: str = ""
    original_value: str = ""
    normalized_value: str = ""
    status: str = "needs_review"

    def to_row(self) -> dict[str, str]:
        return {
            "review_id": self.review_id,
            "source": self.source,
            "adapter_id": self.adapter_id,
            "scope": self.scope,
            "kind": self.kind,
            "message": self.message,
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "field_name": self.field_name,
            "original_value": self.original_value,
            "normalized_value": self.normalized_value,
            "status": self.status,
        }


@dataclass(frozen=True)
class WalletInventoryRecord:
    wallet_id: str
    source: str
    account: str
    wallet: str
    evidence_path: str
    identifier_kind: str
    identifier_value: str
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "wallet_id": self.wallet_id,
            "source": self.source,
            "account": self.account,
            "wallet": self.wallet,
            "evidence_path": self.evidence_path,
            "identifier_kind": self.identifier_kind,
            "identifier_value": self.identifier_value,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SourceProfile:
    source: SourceId
    raw_dir: str
    adapter_id: AdapterId
    manifest_fingerprint: str
    file_inventory: tuple[FileInventoryEntry, ...]
    supported: bool
    metadata: dict[str, str] = field(default_factory=_empty_metadata)
    timezone_summary: dict[str, object] = field(default_factory=_empty_object_map)
    timezone_issues: tuple[IssueRecord, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "raw_dir": self.raw_dir,
            "adapter_id": str(self.adapter_id),
            "manifest_fingerprint": self.manifest_fingerprint,
            "supported": self.supported,
            "metadata": dict(self.metadata),
            "timezone_summary": dict(self.timezone_summary),
            "file_inventory": [
                {
                    "relative_path": item.relative_path,
                    "suffix": item.suffix,
                    "size_bytes": item.size_bytes,
                    "sha256": item.sha256,
                    "row_count": item.row_count,
                    "header": list(item.header),
                    "timestamp_resolution": item.timestamp_resolution,
                    "timezone_mode": item.timezone_mode,
                    "timezone_value": item.timezone_value,
                    "timezone_conflict": item.timezone_conflict,
                }
                for item in self.file_inventory
            ],
        }


@dataclass(frozen=True)
class VerificationExportSet:
    validate_transactions: str
    missing_transactions: str
    duplicate_transactions: str
    current_balance: str
    balance_by_exchange: str
