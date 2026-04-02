"""Shared adapter translation-batch helpers."""

from __future__ import annotations

from collections.abc import Iterable

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import EconomicLeg, FactSemantics, TransactionFact
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_translation import EconomicActivityDraft, SourceTranslationBatch


def compile_activity_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[TransactionFact, ...]:
    return transaction_facts_from_drafts(drafts)


def translation_batch_from_drafts(
    drafts: Iterable[EconomicActivityDraft] = (),
    *,
    balance_evidence: Iterable[BalanceEvidence] = (),
    issues: Iterable[IssueRecord] = (),
    reviews: Iterable[NormalizationReviewRecord] = (),
    location_inventory: Iterable[LocationInventoryRecord] = (),
) -> SourceTranslationBatch:
    return SourceTranslationBatch(
        drafts=tuple(drafts),
        balance_evidence=tuple(balance_evidence),
        issues=tuple(issues),
        reviews=tuple(reviews),
        location_inventory=tuple(location_inventory),
    )


def compile_activity_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return transaction_fact_from_draft(draft)


def transaction_fact_from_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return TransactionFact(
        fact_id=TransactionId(draft.activity_id),
        source=SourceId(draft.source),
        adapter_id=AdapterId(draft.adapter_id),
        timestamp=draft.timestamp,
        location_id=draft.location_id,
        semantics=FactSemantics(
            economic_kind=draft.classification.economic_kind,
            accounting_intent_hint=draft.classification.accounting_intent_hint,
            tax_treatment_hint=draft.classification.tax_treatment_hint,
            projection_hint=draft.classification.projection_hint,
        ),
        legs=tuple(
            EconomicLeg(
                direction=leg.direction,
                kind=leg.kind,
                asset=AssetSymbol(leg.asset),
                amount=leg.amount,
                subtype=leg.subtype,
                attributed_to_direction=leg.attributed_to_direction,
                location_id=leg.location_id,
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
