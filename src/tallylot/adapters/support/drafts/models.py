"""Adapter draft model re-exports."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.locations import LocationKind, LocationRecord
from tallylot.domain.transactions import (
    SINGLE_PRIMARY_ACTIVITY_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_POLICY,
    TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY,
    AccountingIntentHint,
    EconomicKind,
    FactLegPolicy,
    LegKind,
    LegShapeLimit,
    ProjectionHint,
    TaxTreatmentHint,
)
from tallylot.ports.annotations import AdapterMetadata
from tallylot.ports.source_translation import (
    ActivityClassification,
    ActivityDraftSeed,
    EconomicActivityDraft,
    EconomicLegDraft,
    LocationDraft,
    classification,
    economic_leg,
    symbol_claim,
)


@dataclass(frozen=True)
class ActivitySemantics:
    economic_kind: EconomicKind
    projection_hint: ProjectionHint
    accounting_intent_hint: AccountingIntentHint
    tax_treatment_hint: TaxTreatmentHint

    def to_classification(self) -> ActivityClassification:
        return classification(
            economic_kind=self.economic_kind,
            projection_hint=self.projection_hint,
            accounting_intent_hint=self.accounting_intent_hint,
            tax_treatment_hint=self.tax_treatment_hint,
        )


__all__ = [
    "SINGLE_PRIMARY_ACTIVITY_POLICY",
    "TWO_SIDED_PRIMARY_EXCHANGE_POLICY",
    "TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY",
    "AccountingIntentHint",
    "ActivityClassification",
    "ActivityDraftSeed",
    "ActivitySemantics",
    "AdapterMetadata",
    "EconomicActivityDraft",
    "EconomicLegDraft",
    "FactLegPolicy",
    "LegKind",
    "LegShapeLimit",
    "LocationDraft",
    "LocationKind",
    "LocationRecord",
    "ProjectionHint",
    "TaxTreatmentHint",
    "classification",
    "economic_leg",
    "symbol_claim",
]
