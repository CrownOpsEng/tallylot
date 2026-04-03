"""Shared adapter translation-batch helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tallylot.adapters.support.issues import IssueSpec, ReviewSpec, issue_record, review_record
from tallylot.domain.instruments import (
    InstrumentId,
    InstrumentIdentifierRecord,
    InstrumentIdentityClaim,
    InstrumentKind,
    InstrumentRecord,
)
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import EconomicLeg, FactSemantics, TransactionFact
from tallylot.domain.types import AdapterId, SourceId, TransactionId
from tallylot.domain.value_objects import format_timestamp
from tallylot.ports.evidence import LocationInventoryRecord
from tallylot.ports.source_translation import EconomicActivityDraft, SourceTranslationBatch


@dataclass(frozen=True)
class DraftCompilationResult:
    facts: tuple[TransactionFact, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]


def compile_activity_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[TransactionFact, ...]:
    return compile_activity_drafts_with_feedback(drafts).facts


def compile_activity_drafts_with_feedback(drafts: tuple[EconomicActivityDraft, ...]) -> DraftCompilationResult:
    facts: list[TransactionFact] = []
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    for draft in drafts:
        compiled_fact, compile_issues, compile_reviews = _compile_activity_draft(draft)
        issues.extend(compile_issues)
        reviews.extend(compile_reviews)
        if compiled_fact is not None:
            facts.append(compiled_fact)
    return DraftCompilationResult(facts=tuple(facts), issues=tuple(issues), reviews=tuple(reviews))


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
    fact, issues, reviews = _compile_activity_draft(draft)
    if issues or reviews or fact is None:
        raise ValueError(f"draft {draft.activity_id} did not resolve to a canonical fact")
    return fact


def _compile_activity_draft(
    draft: EconomicActivityDraft,
) -> tuple[TransactionFact | None, tuple[IssueRecord, ...], tuple[NormalizationReviewRecord, ...]]:
    issues: list[IssueRecord] = []
    reviews: list[NormalizationReviewRecord] = []
    legs: list[EconomicLeg] = []
    for leg in draft.legs:
        resolution = _resolve_instrument_identity(leg.instrument_identity_claims)
        if resolution is None:
            issues.append(_blocking_identity_issue(draft, leg.leg_id))
            reviews.append(_identity_review(draft, leg.leg_id, leg.instrument_identity_claims))
            continue
        legs.append(
            EconomicLeg(
                leg_id=leg.leg_id,
                kind=leg.kind,
                instrument_id=resolution.instrument.instrument_id,
                quantity=leg.quantity,
                subtype=leg.subtype,
                attributed_to_leg_id=leg.attributed_to_leg_id,
                location_id=leg.location_id,
            )
        )
    if issues or reviews:
        return None, tuple(issues), tuple(reviews)
    return (
        TransactionFact(
            fact_id=TransactionId(draft.activity_id),
            source=SourceId(draft.source),
            adapter_id=AdapterId(draft.adapter_id),
            timestamp=draft.timestamp,
            effective_at=draft.effective_at,
            effective_precision=draft.effective_precision,
            location_id=draft.location_id,
            semantics=FactSemantics(
                economic_kind=draft.classification.economic_kind,
                accounting_intent_hint=draft.classification.accounting_intent_hint,
                tax_treatment_hint=draft.classification.tax_treatment_hint,
                projection_hint=draft.classification.projection_hint,
            ),
            legs=tuple(legs),
            leg_policy=draft.leg_policy,
            description=draft.description,
            provider_operation_key=draft.provider_operation_key,
            operation_group_id=draft.operation_group_id,
            tx_hash=draft.tx_hash or None,
            raw_file=draft.raw_file,
            raw_row_ref=draft.raw_row_ref,
            confidence=draft.confidence,
            status=draft.status,
        ),
        (),
        (),
    )


def transaction_facts_from_drafts(drafts: tuple[EconomicActivityDraft, ...]) -> tuple[TransactionFact, ...]:
    return tuple(transaction_fact_from_draft(draft) for draft in drafts)


@dataclass(frozen=True)
class _ResolvedInstrument:
    instrument: InstrumentRecord
    identifiers: tuple[InstrumentIdentifierRecord, ...]


def _resolve_instrument_identity(claims: tuple[InstrumentIdentityClaim, ...]) -> _ResolvedInstrument | None:
    normalized_claims = tuple(_normalize_claim(claim) for claim in claims)
    unique_keys = {(_claim_key(claim)) for claim in normalized_claims}
    if len(unique_keys) != 1:
        return None
    kinds = {claim.kind_hint for claim in normalized_claims if claim.kind_hint is not InstrumentKind.UNKNOWN}
    if len(kinds) > 1:
        return None
    precisions = {claim.precision_hint for claim in normalized_claims if claim.precision_hint is not None}
    if len(precisions) > 1:
        return None
    representative = normalized_claims[0]
    instrument_id = InstrumentId(_instrument_id_text(representative))
    display_name = next((claim.display_name for claim in normalized_claims if claim.display_name), representative.value)
    return _ResolvedInstrument(
        instrument=InstrumentRecord(
            instrument_id=instrument_id,
            kind=next(iter(kinds), InstrumentKind.UNKNOWN),
            display_name=display_name,
            precision=next(iter(precisions), None),
        ),
        identifiers=tuple(
            InstrumentIdentifierRecord(
                instrument_id=instrument_id,
                scheme=claim.scheme,
                value=claim.value,
                venue=claim.venue,
            )
            for claim in normalized_claims
        ),
    )


def _normalize_claim(claim: InstrumentIdentityClaim) -> InstrumentIdentityClaim:
    normalized_value = claim.value.strip()
    if claim.scheme == "symbol":
        normalized_value = normalized_value.upper()
    normalized_venue = None if claim.venue is None or not claim.venue.strip() else claim.venue.strip().lower()
    return InstrumentIdentityClaim(
        scheme=claim.scheme.strip(),
        value=normalized_value,
        venue=normalized_venue,
        kind_hint=claim.kind_hint,
        display_name=claim.display_name.strip(),
        precision_hint=claim.precision_hint,
    )


def _claim_key(claim: InstrumentIdentityClaim) -> tuple[str, str, str]:
    return claim.scheme, claim.value, "" if claim.venue is None else claim.venue


def _instrument_id_text(claim: InstrumentIdentityClaim) -> str:
    venue_suffix = "" if claim.venue is None else f"@{claim.venue}"
    return f"{claim.scheme}:{claim.value}{venue_suffix}"


def _blocking_identity_issue(draft: EconomicActivityDraft, leg_id: str) -> IssueRecord:
    return issue_record(
        IssueSpec(
            issue_id=f"{draft.activity_id}:{leg_id}:instrument_identity_blocked",
            source=draft.source,
            adapter_id=draft.adapter_id,
            severity="high",
            kind="instrument_identity_blocked",
            message=f"Activity {draft.activity_id} could not resolve leg {leg_id} to exactly one instrument.",
            context_timestamp=format_timestamp(draft.timestamp),
            raw_file=draft.raw_file,
            raw_row_ref=draft.raw_row_ref,
        )
    )


def _identity_review(
    draft: EconomicActivityDraft,
    leg_id: str,
    claims: tuple[InstrumentIdentityClaim, ...],
) -> NormalizationReviewRecord:
    claims_text = ", ".join(
        f"{claim.scheme}={claim.value}" if claim.venue in (None, "") else f"{claim.scheme}={claim.value}@{claim.venue}"
        for claim in claims
    )
    return review_record(
        ReviewSpec(
            review_id=f"{draft.activity_id}:{leg_id}:instrument_identity_review",
            source=draft.source,
            adapter_id=draft.adapter_id,
            scope="activity",
            kind="instrument_identity_review",
            message=f"Review required for leg {leg_id} instrument identity claims.",
            context_timestamp=format_timestamp(draft.timestamp),
            raw_file=draft.raw_file,
            raw_row_ref=draft.raw_row_ref,
            field_name="instrument_identity_claims",
            original_value=claims_text,
            normalized_value="",
        )
    )
