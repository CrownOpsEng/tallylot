"""Shared mapped-event construction for source adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_reconciliation.domain.models import CanonicalEvent, IssueRecord
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId


@dataclass(frozen=True)
class MappedEventSpec:
    event_id: str
    source: str
    adapter_id: str
    account: str
    wallet: str
    timestamp: datetime
    event_kind: str
    description: str
    raw_file: str
    raw_row_ref: str
    render_exchange: str
    asset_in: str = ""
    amount_in: Decimal | None = None
    asset_out: str = ""
    amount_out: Decimal | None = None
    fee_asset: str = ""
    fee_amount: Decimal | None = None
    tx_hash: str = ""
    render_group: str = ""
    render_comment: str = ""
    render_comment_mode: str = "exact"
    render_tx_id: str = ""
    render_tx_id_mode: str = "ignore"
    render_allowed_types: str = ""
    render_match_window_seconds: str = "0"
    render_fee_tolerance: str = "0.00000000"
    render_notes: str = ""


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


def mapped_event(spec: MappedEventSpec) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=EventId(spec.event_id),
        source=SourceId(spec.source),
        adapter_id=AdapterId(spec.adapter_id),
        account=spec.account,
        wallet=spec.wallet,
        timestamp=spec.timestamp,
        event_kind=spec.event_kind,
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
        render_type=spec.event_kind,
        render_exchange=spec.render_exchange,
        render_group=spec.render_group,
        render_comment=spec.render_comment or spec.description,
        render_comment_mode=spec.render_comment_mode,
        render_tx_id=spec.render_tx_id,
        render_tx_id_mode=spec.render_tx_id_mode,
        render_allowed_types=spec.render_allowed_types or spec.event_kind,
        render_match_window_seconds=spec.render_match_window_seconds,
        render_fee_tolerance=spec.render_fee_tolerance,
        render_notes=spec.render_notes,
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
