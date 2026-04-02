"""Source translation batch contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, TypeVar

from crypto_reconciliation.domain.checkpoints import BalanceEvidence
from crypto_reconciliation.domain.issues import IssueRecord, NormalizationReviewRecord
from crypto_reconciliation.domain.transactions import (
    EconomicKind,
    EconomicLeg,
    FactClassification,
    JournalIntent,
    ProjectionType,
    TaxTreatmentCode,
    TransactionFact,
    parse_economic_kind,
    parse_journal_intent,
    parse_projection_type,
    parse_tax_treatment_code,
)
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from crypto_reconciliation.ports.evidence import WalletInventoryRecord

DraftDirection = Literal["in", "out"]
EnumT = TypeVar("EnumT")


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
    economic_kind: EconomicKind | str,
    projection_type: ProjectionType | str | None = None,
    journal_intent: JournalIntent | str,
    tax_treatment_code: TaxTreatmentCode | str,
) -> ActivityClassification:
    return ActivityClassification(
        economic_kind=(
            economic_kind
            if isinstance(economic_kind, EconomicKind)
            else _require_enum(parse_economic_kind(economic_kind), "EconomicKind")
        ),
        projection_type=(
            projection_type
            if isinstance(projection_type, ProjectionType)
            else parse_projection_type("" if projection_type is None else projection_type)
        ),
        journal_intent=(
            journal_intent
            if isinstance(journal_intent, JournalIntent)
            else _require_enum(parse_journal_intent(journal_intent), "JournalIntent")
        ),
        tax_treatment_code=(
            tax_treatment_code
            if isinstance(tax_treatment_code, TaxTreatmentCode)
            else _require_enum(parse_tax_treatment_code(tax_treatment_code), "TaxTreatmentCode")
        ),
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


def _require_enum(value: EnumT | None, enum_name: str) -> EnumT:
    if value is None:
        raise ValueError(f"{enum_name} value is required")
    return value
