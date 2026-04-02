"""Draft-to-fact translation helpers."""

from __future__ import annotations

from crypto_reconciliation.domain.transactions import EconomicLeg, FactClassification, TransactionFact
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId

from .models import EconomicActivityDraft


def transaction_fact_from_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(draft.activity_id),
        source=SourceId(draft.source),
        adapter_id=AdapterId(draft.adapter_id),
        timestamp=draft.timestamp,
        account=draft.account,
        wallet=draft.wallet,
        classification=FactClassification(
            economic_kind=draft.classification.economic_kind,
            journal_intent=draft.classification.journal_intent,
            tax_treatment_code=draft.classification.tax_treatment_code,
            projection_type=draft.classification.projection_type,
        ),
        legs=tuple(
            EconomicLeg(
                direction=leg.direction,
                asset=AssetSymbol(leg.asset),
                amount=leg.amount,
                account=leg.account,
                wallet=leg.wallet,
            )
            for leg in draft.legs
        ),
        fee_legs=tuple(
            EconomicLeg(
                direction=leg.direction,
                asset=AssetSymbol(leg.asset),
                amount=leg.amount,
                account=leg.account,
                wallet=leg.wallet,
            )
            for leg in draft.fee_legs
        ),
        description=draft.description,
        provider_operation_key=draft.provider_operation_key,
        operation_group_id=draft.operation_group_id,
        tx_hash=draft.tx_hash or None,
        raw_file=draft.raw_file,
        raw_row_ref=draft.raw_row_ref,
        confidence=draft.confidence,
        status=draft.status,
    )


def transaction_facts_from_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[TransactionFact, ...]:
    return tuple(transaction_fact_from_draft(draft) for draft in drafts)
