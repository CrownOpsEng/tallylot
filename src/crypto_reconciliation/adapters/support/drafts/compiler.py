"""Compile adapter drafts into the current normalized runtime shape."""

from __future__ import annotations

from collections.abc import Iterable

from crypto_reconciliation.domain.models import (
    BalanceSnapshot,
    IssueRecord,
    NormalizationReviewRecord,
    NormalizedTransaction,
    WalletInventoryRecord,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.ports.adapters import NormalizationResult

from .models import EconomicActivityDraft


def compile_activity_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[NormalizedTransaction, ...]:
    return tuple(compile_activity_draft(draft) for draft in drafts)


def normalization_result_from_drafts(
    drafts: Iterable[EconomicActivityDraft] = (),
    *,
    balance_evidence: Iterable[BalanceSnapshot] = (),
    issues: Iterable[IssueRecord] = (),
    reviews: Iterable[NormalizationReviewRecord] = (),
    wallet_inventory: Iterable[WalletInventoryRecord] = (),
) -> NormalizationResult:
    draft_rows = tuple(drafts)
    return NormalizationResult(
        transactions=compile_activity_drafts(draft_rows),
        balance_evidence=tuple(balance_evidence),
        issues=tuple(issues),
        reviews=tuple(reviews),
        wallet_inventory=tuple(wallet_inventory),
    )


def compile_activity_draft(draft: EconomicActivityDraft) -> NormalizedTransaction:
    inbound_legs = tuple(leg for leg in draft.legs if leg.direction == "in")
    outbound_legs = tuple(leg for leg in draft.legs if leg.direction == "out")
    if len(inbound_legs) > 1 or len(outbound_legs) > 1 or len(draft.fee_legs) > 1:
        raise ValueError(
            "current normalized transaction compatibility compiler supports at most one inbound leg, "
            "one outbound leg, and one fee leg"
        )
    projection = draft.projection
    inbound_leg = inbound_legs[0] if inbound_legs else None
    outbound_leg = outbound_legs[0] if outbound_legs else None
    fee = draft.fee_legs[0] if draft.fee_legs else None
    return NormalizedTransaction(
        transaction_id=TransactionId(draft.activity_id),
        source=SourceId(draft.source),
        adapter_id=AdapterId(draft.adapter_id),
        account=draft.account,
        wallet=draft.wallet,
        timestamp=draft.timestamp,
        category=draft.classification.normalized_category,
        economic_kind=draft.classification.economic_kind,
        projection_type=draft.classification.projection_type,
        journal_intent=draft.classification.journal_intent,
        tax_treatment_code=draft.classification.tax_treatment_code,
        provider_operation_key=draft.provider_operation_key,
        group_key=projection.group if projection is not None else draft.group_key,
        description=draft.description,
        asset_in=AssetSymbol(inbound_leg.asset) if inbound_leg is not None else None,
        amount_in=inbound_leg.amount if inbound_leg is not None else None,
        asset_out=AssetSymbol(outbound_leg.asset) if outbound_leg is not None else None,
        amount_out=outbound_leg.amount if outbound_leg is not None else None,
        fee_asset=AssetSymbol(fee.asset) if fee is not None else None,
        fee_amount=fee.amount if fee is not None else None,
        tx_hash=draft.tx_hash or None,
        raw_file=draft.raw_file,
        raw_row_ref=draft.raw_row_ref,
        confidence=draft.confidence,
        status=draft.status,
    )
