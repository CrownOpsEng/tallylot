"""Shared transaction construction for source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_reconciliation.domain.models import (
    IssueRecord,
    NormalizedTransaction,
    TransactionCategory,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId


@dataclass(frozen=True)
class MappedTransactionSpec:
    transaction_id: str
    source: str
    adapter_id: str
    account: str
    wallet: str
    timestamp: datetime
    category: TransactionCategory
    description: str
    raw_file: str
    raw_row_ref: str
    asset_in: str = ""
    amount_in: Decimal | None = None
    asset_out: str = ""
    amount_out: Decimal | None = None
    fee_asset: str = ""
    fee_amount: Decimal | None = None
    tx_hash: str = ""


@dataclass(frozen=True)
class NormalizationIssueSpec:
    source: str
    adapter_id: str
    issue_id: str
    kind: str
    message: str
    raw_file: str = ""
    raw_row_ref: str = ""
    severity: str = "medium"
    status: str = "needs_review"


def mapped_transaction(spec: MappedTransactionSpec) -> NormalizedTransaction:
    return NormalizedTransaction(
        transaction_id=TransactionId(spec.transaction_id),
        source=SourceId(spec.source),
        adapter_id=AdapterId(spec.adapter_id),
        account=spec.account,
        wallet=spec.wallet,
        timestamp=spec.timestamp,
        category=spec.category,
        description=spec.description,
        asset_in=AssetSymbol(spec.asset_in) if spec.asset_in else None,
        amount_in=spec.amount_in,
        asset_out=AssetSymbol(spec.asset_out) if spec.asset_out else None,
        amount_out=spec.amount_out,
        fee_asset=AssetSymbol(spec.fee_asset) if spec.fee_asset else None,
        fee_amount=spec.fee_amount,
        tx_hash=spec.tx_hash or None,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
    )


def normalization_issue(spec: NormalizationIssueSpec) -> IssueRecord:
    return IssueRecord(
        issue_id=spec.issue_id,
        source=spec.source,
        adapter_id=spec.adapter_id,
        severity=spec.severity,
        kind=spec.kind,
        message=spec.message,
        raw_file=spec.raw_file,
        raw_row_ref=spec.raw_row_ref,
        status=spec.status,
    )
