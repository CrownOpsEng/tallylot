"""Shared adapter translation-batch helpers."""

from __future__ import annotations

from collections.abc import Iterable

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import EconomicLeg, FactClassification, TransactionFact
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.ports.evidence import WalletInventoryRecord
from tallylot.ports.source_translation import EconomicActivityDraft, SourceTranslationBatch


def compile_activity_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[TransactionFact, ...]:
    return transaction_facts_from_drafts(drafts)


def translation_batch_from_drafts(
    drafts: Iterable[EconomicActivityDraft] = (),
    *,
    balance_evidence: Iterable[BalanceEvidence] = (),
    issues: Iterable[IssueRecord] = (),
    reviews: Iterable[NormalizationReviewRecord] = (),
    wallet_inventory: Iterable[WalletInventoryRecord] = (),
) -> SourceTranslationBatch:
    return SourceTranslationBatch(
        drafts=tuple(drafts),
        balance_evidence=tuple(balance_evidence),
        issues=tuple(issues),
        reviews=tuple(reviews),
        wallet_inventory=tuple(wallet_inventory),
    )


def compile_activity_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return transaction_fact_from_draft(draft)


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
                kind=leg.kind,
                asset=AssetSymbol(leg.asset),
                amount=leg.amount,
                subtype=leg.subtype,
                attributed_to_direction=leg.attributed_to_direction,
                account=leg.account,
                wallet=leg.wallet,
            )
            for leg in draft.legs
        ),
        leg_policy=draft.leg_policy,
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
