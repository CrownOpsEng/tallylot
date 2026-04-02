"""Adapter draft models aligned to the future fact-oriented translation seam."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from crypto_reconciliation.domain.models import TransactionCategory

DraftDirection = Literal["in", "out"]


@dataclass(frozen=True)
class ActivityClassification:
    normalized_category: TransactionCategory
    economic_kind: str
    projection_type: str
    journal_intent: str
    tax_treatment_code: str


@dataclass(frozen=True)
class CompatibilityProjection:
    row_type: str
    group: str = ""
    comment: str = ""
    tx_id: str = ""


@dataclass(frozen=True)
class ActivityDraftSeed:
    activity_id: str
    timestamp: datetime
    description: str = ""
    raw_file: str = ""
    raw_row_ref: str = ""
    tx_hash: str = ""
    provider_operation_key: str = ""
    group_key: str = ""
    provenance_refs: tuple[str, ...] = ()
    review_markers: tuple[str, ...] = ()
    confidence: str = "high"
    status: str = "mapped"
    projection: CompatibilityProjection | None = None


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
    group_key: str = ""
    provenance_refs: tuple[str, ...] = ()
    review_markers: tuple[str, ...] = ()
    confidence: str = "high"
    status: str = "mapped"
    projection: CompatibilityProjection | None = None

    def __post_init__(self) -> None:
        if not self.legs:
            raise ValueError("draft must include at least one economic leg")


def classification(
    *,
    normalized_category: TransactionCategory,
    economic_kind: str,
    projection_type: str,
    journal_intent: str,
    tax_treatment_code: str,
) -> ActivityClassification:
    return ActivityClassification(
        normalized_category=normalized_category,
        economic_kind=economic_kind,
        projection_type=projection_type,
        journal_intent=journal_intent,
        tax_treatment_code=tax_treatment_code,
    )


def compatibility_projection(
    *,
    row_type: str,
    group: str = "",
    comment: str = "",
    tx_id: str = "",
) -> CompatibilityProjection:
    return CompatibilityProjection(row_type=row_type, group=group, comment=comment, tx_id=tx_id)


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
