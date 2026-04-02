"""Source translation batch contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    FactLegPolicy,
    JournalIntent,
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
    leg_policy: FactLegPolicy = field(default_factory=FactLegPolicy)
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
    asset: str
    amount: Decimal
    account: str = ""
    wallet: str = ""

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise ValueError("draft leg amount must be greater than zero")
        if not self.asset:
            raise ValueError("draft leg asset must be present")


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
    leg_policy: FactLegPolicy = field(default_factory=FactLegPolicy)
    fee_legs: tuple[EconomicLegDraft, ...] = ()
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
            raise ValueError("draft must include at least one economic leg")
        inbound_legs = sum(1 for leg in self.legs if leg.direction == "in")
        outbound_legs = sum(1 for leg in self.legs if leg.direction == "out")
        if inbound_legs > self.leg_policy.max_in_legs:
            raise ValueError("draft inbound legs exceed declared leg policy")
        if outbound_legs > self.leg_policy.max_out_legs:
            raise ValueError("draft outbound legs exceed declared leg policy")
        if len(self.fee_legs) > self.leg_policy.max_fee_legs:
            raise ValueError("draft fee legs exceed declared leg policy")


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


def economic_leg(
    *,
    direction: DraftDirection,
    asset: str,
    amount: Decimal,
    account: str = "",
    wallet: str = "",
) -> EconomicLegDraft:
    return EconomicLegDraft(direction=direction, asset=asset, amount=amount, account=account, wallet=wallet)


def fee_leg(
    *,
    asset: str,
    amount: Decimal,
    account: str = "",
    wallet: str = "",
) -> EconomicLegDraft:
    return EconomicLegDraft(direction="out", asset=asset, amount=amount, account=account, wallet=wallet)


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
        leg_policy=draft.leg_policy,
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
