"""Source translation batch contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.locations import LocationKind, LocationRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactDirection,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, AssetSymbol, LocationId, SourceId, TransactionId
from tallylot.domain.value_objects import require_utc_datetime
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.evidence import LocationInventoryRecord

DraftDirection = Literal["in", "out"]


@dataclass(frozen=True)
class ActivityClassification:
    economic_kind: EconomicKind
    projection_hint: ProjectionHint | None
    accounting_intent_hint: AccountingIntentHint
    tax_treatment_hint: TaxTreatmentHint


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
    adapter_metadata: tuple[AdapterMetadata, ...] = ()
    confidence: str = "high"
    status: str = "mapped"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "timestamp",
            require_utc_datetime(self.timestamp, label="activity draft seed timestamp"),
        )


@dataclass(frozen=True)
class EconomicLegDraft:
    direction: DraftDirection
    kind: LegKind
    asset: str
    amount: Decimal
    subtype: str | None = None
    attributed_to_direction: FactDirection | None = None
    location_id: LocationId | None = None

    def __post_init__(self) -> None:
        EconomicLeg(
            direction=self.direction,
            kind=self.kind,
            asset=AssetSymbol(self.asset),
            amount=self.amount,
            subtype=self.subtype,
            attributed_to_direction=self.attributed_to_direction,
            location_id=self.location_id,
        )


@dataclass(frozen=True)
class EconomicActivityDraft:
    activity_id: str
    source: str
    adapter_id: str
    timestamp: datetime
    location_id: LocationId
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
    adapter_metadata: tuple[AdapterMetadata, ...] = ()
    confidence: str = "high"
    status: str = "mapped"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "timestamp",
            require_utc_datetime(self.timestamp, label="economic activity draft timestamp"),
        )
        if not self.legs:
            raise ValueError("draft must include at least one leg")
        _validated_transaction_fact(self)


@dataclass(frozen=True)
class SourceTranslationBatch:
    drafts: tuple[EconomicActivityDraft, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]


@dataclass(frozen=True)
class LocationDraft:
    location_id: LocationId
    location_kind: LocationKind
    label: str
    parent_location_id: LocationId | None = None
    path: tuple[str, ...] = ()

    def to_record(self) -> LocationRecord:
        return LocationRecord(
            location_id=self.location_id,
            location_kind=self.location_kind,
            label=self.label,
            parent_location_id=self.parent_location_id,
            path=self.path,
        )


def classification(
    *,
    economic_kind: EconomicKind,
    projection_hint: ProjectionHint | None = None,
    accounting_intent_hint: AccountingIntentHint,
    tax_treatment_hint: TaxTreatmentHint,
) -> ActivityClassification:
    return ActivityClassification(
        economic_kind=economic_kind,
        projection_hint=projection_hint,
        accounting_intent_hint=accounting_intent_hint,
        tax_treatment_hint=tax_treatment_hint,
    )


def economic_leg(  # pylint: disable=too-many-arguments
    *,
    direction: DraftDirection,
    kind: LegKind,
    asset: str,
    amount: Decimal,
    subtype: str | None = None,
    attributed_to_direction: FactDirection | None = None,
    location_id: LocationId | None = None,
) -> EconomicLegDraft:
    return EconomicLegDraft(
        direction=direction,
        kind=kind,
        asset=asset,
        amount=amount,
        subtype=subtype,
        attributed_to_direction=attributed_to_direction,
        location_id=location_id,
    )


def _validated_transaction_fact(draft: EconomicActivityDraft) -> TransactionFact:
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
