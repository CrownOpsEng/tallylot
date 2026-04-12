"""Source translation batch contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.instruments import (
    InstrumentId,
    InstrumentIdentityClaim,
    InstrumentKind,
)
from tallylot.domain.balances import BalanceReference
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.locations import LocationKind, LocationRecord
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import (
    AccountingIntentHint,
    EconomicKind,
    EconomicLeg,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    ProjectionHint,
    TaxTreatmentHint,
    TransactionFact,
)
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.value_objects import (
    require_temporal_datetime,
    require_utc_datetime,
)
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.evidence import LocationInventoryRecord


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
    effective_at: datetime | None = None
    effective_precision: TemporalPrecision | None = None
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
        if self.effective_at is None:
            if self.effective_precision is not None:
                raise ValueError(
                    "activity draft seed effective_precision requires effective_at"
                )
        else:
            if self.effective_precision is None:
                raise ValueError(
                    "activity draft seed effective_at requires effective_precision"
                )
            object.__setattr__(
                self,
                "effective_at",
                require_temporal_datetime(
                    self.effective_at,
                    precision=self.effective_precision,
                    label="activity draft seed effective_at",
                ),
            )


@dataclass(frozen=True)
class EconomicLegDraft:
    leg_id: str
    kind: LegKind
    instrument_identity_claims: tuple[InstrumentIdentityClaim, ...]
    quantity: Decimal
    subtype: str | None = None
    attributed_to_leg_id: str | None = None
    location_id: LocationId | None = None

    def __post_init__(self) -> None:
        if not self.instrument_identity_claims:
            raise ValueError(
                "draft leg must include at least one instrument identity claim"
            )
        EconomicLeg(
            leg_id=self.leg_id,
            kind=self.kind,
            instrument_id=InstrumentId("draft:placeholder"),
            quantity=self.quantity,
            subtype=self.subtype,
            attributed_to_leg_id=self.attributed_to_leg_id,
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
    effective_at: datetime | None = None
    effective_precision: TemporalPrecision | None = None
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
            require_utc_datetime(
                self.timestamp, label="economic activity draft timestamp"
            ),
        )
        object.__setattr__(
            self,
            "location_id",
            require_location_id(
                str(self.location_id), label="economic activity draft location_id"
            ),
        )
        if self.effective_at is None:
            if self.effective_precision is not None:
                raise ValueError(
                    "economic activity draft effective_precision requires effective_at"
                )
        else:
            if self.effective_precision is None:
                raise ValueError(
                    "economic activity draft effective_at requires effective_precision"
                )
            object.__setattr__(
                self,
                "effective_at",
                require_temporal_datetime(
                    self.effective_at,
                    precision=self.effective_precision,
                    label="economic activity draft effective_at",
                ),
            )
        if not self.legs:
            raise ValueError("draft must include at least one leg")
        _validated_transaction_fact(self)


@dataclass(frozen=True)
class SourceTranslationBatch:
    drafts: tuple[EconomicActivityDraft, ...]
    balance_references: tuple[BalanceReference, ...]
    balance_reference_issues: tuple[IssueRecord, ...]
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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "location_id",
            require_location_id(
                str(self.location_id), label="location draft location_id"
            ),
        )
        if self.parent_location_id is not None:
            object.__setattr__(
                self,
                "parent_location_id",
                require_location_id(
                    str(self.parent_location_id),
                    label="location draft parent_location_id",
                ),
            )

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
    leg_id: str,
    kind: LegKind,
    quantity: Decimal,
    instrument: str | InstrumentIdentityClaim | tuple[InstrumentIdentityClaim, ...],
    subtype: str | None = None,
    attributed_to_leg_id: str | None = None,
    location_id: LocationId | None = None,
) -> EconomicLegDraft:
    return EconomicLegDraft(
        leg_id=leg_id,
        kind=kind,
        instrument_identity_claims=_identity_claims(instrument),
        quantity=quantity,
        subtype=subtype,
        attributed_to_leg_id=attributed_to_leg_id,
        location_id=location_id,
    )


def _validated_transaction_fact(draft: EconomicActivityDraft) -> TransactionFact:
    return TransactionFact(
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
        legs=tuple(
            EconomicLeg(
                leg_id=leg.leg_id,
                kind=leg.kind,
                instrument_id=InstrumentId("draft:placeholder"),
                quantity=leg.quantity,
                subtype=leg.subtype,
                attributed_to_leg_id=leg.attributed_to_leg_id,
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


def symbol_claim(
    value: str,
    *,
    display_name: str = "",
    kind_hint: InstrumentKind = InstrumentKind.UNKNOWN,
    precision_hint: int | None = None,
    venue: str | None = None,
) -> InstrumentIdentityClaim:
    return InstrumentIdentityClaim(
        scheme="symbol",
        value=value,
        venue=venue,
        kind_hint=kind_hint,
        display_name=display_name,
        precision_hint=precision_hint,
    )


def _identity_claims(
    instrument: str | InstrumentIdentityClaim | tuple[InstrumentIdentityClaim, ...],
) -> tuple[InstrumentIdentityClaim, ...]:
    if isinstance(instrument, tuple):
        return instrument
    if isinstance(instrument, InstrumentIdentityClaim):
        return (instrument,)
    return (symbol_claim(instrument),)
