"""Source translation batch contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    FactDirection,
    FactLegPolicy,
    JournalIntent,
    LegKind,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.ports.evidence import WalletInventoryRecord

DraftDirection = Literal["in", "out"]


@dataclass(frozen=True)
class ActivityClassification:
    economic_kind: EconomicKind
    projection_type: ProjectionType | None
    journal_intent: JournalIntent
    tax_treatment_code: TaxTreatmentCode


@dataclass(frozen=True)
class ActivityDraftSeed:
    activity_id: str
    timestamp: datetime
    leg_policy: FactLegPolicy
    description: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    tx_hash: str = ""
    provider_operation_key: str = ""
    operation_group_id: str = ""
    provenance_refs: tuple[str, ...] = ()
    review_markers: tuple[str, ...] = ()
    confidence: str = "high"
    status: str = "mapped"


@dataclass(frozen=True)
class EconomicLegDraft:
    direction: DraftDirection
    kind: LegKind
    asset: str
    amount: Decimal
    subtype: str | None = None
    attributed_to_direction: FactDirection | None = None
    account: str = ""
    wallet: str = ""

    def __post_init__(self) -> None:
        EconomicLeg(
            direction=self.direction,
            kind=self.kind,
            asset=AssetSymbol(self.asset),
            amount=self.amount,
            subtype=self.subtype,
            attributed_to_direction=self.attributed_to_direction,
            account=self.account,
            wallet=self.wallet,
        )


@dataclass(frozen=True)
class EconomicActivityDraft:
    activity_id: str
    source: str
    adapter_id: str
    timestamp: datetime
    account: str
    wallet: str
    classification: ActivityClassification
    legs: tuple[EconomicLegDraft, ...]
    leg_policy: FactLegPolicy
    description: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    tx_hash: str = ""
    provider_operation_key: str = ""
    operation_group_id: str = ""
    provenance_refs: tuple[str, ...] = ()
    review_markers: tuple[str, ...] = ()
    confidence: str = "high"
    status: str = "mapped"

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("draft must include at least one leg")
        TransactionFact(
            fact_id=TransactionId(self.activity_id),
            source=SourceId(self.source),
            adapter_id=AdapterId(self.adapter_id),
            timestamp=self.timestamp,
            account=self.account,
            wallet=self.wallet,
            classification=FactClassification(
                economic_kind=self.classification.economic_kind,
                journal_intent=self.classification.journal_intent,
                tax_treatment_code=self.classification.tax_treatment_code,
                projection_type=self.classification.projection_type,
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
                for leg in self.legs
            ),
            leg_policy=self.leg_policy,
            description=self.description,
            provider_operation_key=self.provider_operation_key,
            operation_group_id=self.operation_group_id,
            tx_hash=self.tx_hash or None,
            raw_file=self.raw_file,
            raw_row_ref=self.raw_row_ref,
            confidence=self.confidence,
            status=self.status,
        )


@dataclass(frozen=True)
class SourceTranslationBatch:
    drafts: tuple[EconomicActivityDraft, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    wallet_inventory: tuple[WalletInventoryRecord, ...]

    @property
    def facts(self) -> tuple[TransactionFact, ...]:
        return transaction_facts_from_drafts(self.drafts)


def classification(
    *,
    economic_kind: EconomicKind,
    projection_type: ProjectionType | None = None,
    journal_intent: JournalIntent,
    tax_treatment_code: TaxTreatmentCode,
) -> ActivityClassification:
    return ActivityClassification(
        economic_kind=economic_kind,
        projection_type=projection_type,
        journal_intent=journal_intent,
        tax_treatment_code=tax_treatment_code,
    )


def economic_leg(  # pylint: disable=too-many-arguments
    *,
    direction: DraftDirection,
    kind: LegKind,
    asset: str,
    amount: Decimal,
    subtype: str | None = None,
    attributed_to_direction: FactDirection | None = None,
    account: str = "",
    wallet: str = "",
) -> EconomicLegDraft:
    return EconomicLegDraft(
        direction=direction,
        kind=kind,
        asset=asset,
        amount=amount,
        subtype=subtype,
        attributed_to_direction=attributed_to_direction,
        account=account,
        wallet=wallet,
    )


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
