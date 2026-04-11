"""Shared adapter translation-batch helpers."""

from __future__ import annotations

from collections.abc import Iterable

from tallylot.application.facts import compiler as _facts_compiler
from tallylot.domain.balances import BalanceReference
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.transactions import TransactionFact
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_translation import (
    EconomicActivityDraft,
    SourceTranslationBatch,
)

DraftCompilationResult = _facts_compiler.DraftCompilationResult


def compile_activity_drafts(
    drafts: tuple[EconomicActivityDraft, ...],
) -> tuple[TransactionFact, ...]:
    return _facts_compiler.compile_activity_drafts(drafts)


def compile_activity_drafts_with_feedback(
    drafts: tuple[EconomicActivityDraft, ...],
) -> _facts_compiler.DraftCompilationResult:
    return _facts_compiler.compile_activity_drafts_with_feedback(drafts)


def compile_activity_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return _facts_compiler.transaction_fact_from_draft(draft)


def transaction_fact_from_draft(draft: EconomicActivityDraft) -> TransactionFact:
    return _facts_compiler.transaction_fact_from_draft(draft)


def transaction_facts_from_drafts(
    drafts: tuple[EconomicActivityDraft, ...],
) -> tuple[TransactionFact, ...]:
    return _facts_compiler.transaction_facts_from_drafts(drafts)


def translation_batch_from_drafts(  # pylint: disable=too-many-arguments
    drafts: Iterable[EconomicActivityDraft] = (),
    *,
    balance_references: Iterable[BalanceReference] = (),
    balance_reference_issues: Iterable[IssueRecord] = (),
    issues: Iterable[IssueRecord] = (),
    reviews: Iterable[NormalizationReviewRecord] = (),
    location_inventory: Iterable[LocationInventoryRecord] = (),
) -> SourceTranslationBatch:
    return SourceTranslationBatch(
        drafts=tuple(drafts),
        balance_references=tuple(balance_references),
        balance_reference_issues=tuple(balance_reference_issues),
        issues=tuple(issues),
        reviews=tuple(reviews),
        location_inventory=tuple(location_inventory),
    )
