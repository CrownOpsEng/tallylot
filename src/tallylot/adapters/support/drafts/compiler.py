"""Shared adapter translation-batch helpers."""

from __future__ import annotations

from collections.abc import Iterable

from tallylot.domain.checkpoints import BalanceEvidence
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.transactions import TransactionFact
from tallylot.ports.evidence import WalletInventoryRecord
from tallylot.ports.source_translation import EconomicActivityDraft, SourceTranslationBatch

from .facts import transaction_fact_from_draft, transaction_facts_from_drafts


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
