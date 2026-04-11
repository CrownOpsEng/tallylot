"""Provider-neutral transaction fact models."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.location_identifiers import require_location_id
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    format_timestamp,
    require_temporal_datetime,
    require_utc_datetime,
)

from .classification import (
    AccountingIntentHint,
    EconomicKind,
    ProjectionHint,
    TaxTreatmentHint,
)
from .validation import (
    fact_leg_counts,
    validate_fact_counts,
    validate_fact_leg_attribution,
    validate_leg_shape_counts,
    validate_non_negative_count,
)

FACT_SCHEMA_VERSION = 2
_LEG_SUBTYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_LEG_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class LegKind(StrEnum):
    PRIMARY = "primary"
    CHARGE = "charge"
    REBATE = "rebate"
    COLLATERAL = "collateral"
    SETTLEMENT = "settlement"
    FINANCING = "financing"
    WITHHOLDING = "withholding"
    ADJUSTMENT = "adjustment"


@dataclass(frozen=True)
class LegShapeLimit:
    kind: LegKind
    max_count: int
    min_count: int = 0
    max_positive_count: int | None = None
    min_positive_count: int | None = None
    max_negative_count: int | None = None
    min_negative_count: int | None = None

    def __post_init__(self) -> None:
        validate_non_negative_count(self.min_count, label="min_count")
        validate_non_negative_count(self.max_count, label="max_count")
        if self.min_count > self.max_count:
            raise ValueError("leg shape limit min_count must not exceed max_count")
        validate_leg_shape_counts(self)


@dataclass(frozen=True)
class FactLegPolicy:
    limits: tuple[LegShapeLimit, ...]

    def __post_init__(self) -> None:
        if not self.limits:
            raise ValueError(
                "fact leg policy must declare at least one supported leg kind"
            )
        seen_kinds: set[LegKind] = set()
        for limit in self.limits:
            if limit.kind in seen_kinds:
                raise ValueError(f"fact leg policy duplicates kind {limit.kind.value}")
            seen_kinds.add(limit.kind)

    def limit_for(self, kind: LegKind) -> LegShapeLimit | None:
        for limit in self.limits:
            if limit.kind is kind:
                return limit
        return None


@dataclass(frozen=True)
class FactSemantics:
    economic_kind: EconomicKind
    accounting_intent_hint: AccountingIntentHint
    tax_treatment_hint: TaxTreatmentHint
    projection_hint: ProjectionHint | None = None


@dataclass(frozen=True)
class EconomicLeg:
    leg_id: str
    kind: LegKind
    instrument_id: InstrumentId
    quantity: Decimal
    subtype: str | None = None
    attributed_to_leg_id: str | None = None
    location_id: LocationId | None = None

    def __post_init__(self) -> None:
        _validate_leg_id(self.leg_id, label="fact leg_id")
        if not str(self.instrument_id):
            raise ValueError("fact leg instrument_id must not be blank")
        if self.quantity == Decimal("0"):
            raise ValueError("fact leg quantity must not be zero")
        if self.location_id is not None:
            object.__setattr__(
                self,
                "location_id",
                require_location_id(
                    str(self.location_id), label="fact leg location_id"
                ),
            )
        if self.kind is LegKind.PRIMARY and self.attributed_to_leg_id is not None:
            raise ValueError("primary legs must not declare attributed_to_leg_id")
        if self.attributed_to_leg_id is not None:
            _validate_leg_id(
                self.attributed_to_leg_id, label="fact leg attributed_to_leg_id"
            )
        if self.subtype is not None and not _LEG_SUBTYPE_PATTERN.fullmatch(
            self.subtype
        ):
            raise ValueError("fact leg subtype must be lowercase snake_case")


@dataclass(frozen=True)
class TransactionFact:
    fact_id: TransactionId
    source: SourceId
    adapter_id: AdapterId
    timestamp: datetime
    location_id: LocationId
    semantics: FactSemantics
    legs: tuple[EconomicLeg, ...]
    leg_policy: FactLegPolicy
    description: str = ""
    provider_operation_key: str = ""
    operation_group_id: str = ""
    tx_hash: str | None = None
    raw_file: str = ""
    raw_row_ref: str = ""
    confidence: str = "high"
    status: str = "mapped"
    effective_at: datetime | None = None
    effective_precision: TemporalPrecision | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "timestamp",
            require_utc_datetime(self.timestamp, label="transaction fact timestamp"),
        )
        object.__setattr__(
            self,
            "location_id",
            require_location_id(
                str(self.location_id), label="transaction fact location_id"
            ),
        )
        if self.effective_at is None:
            if self.effective_precision is not None:
                raise ValueError(
                    "transaction fact effective_precision requires effective_at"
                )
        else:
            if self.effective_precision is None:
                raise ValueError(
                    "transaction fact effective_at requires effective_precision"
                )
            object.__setattr__(
                self,
                "effective_at",
                require_temporal_datetime(
                    self.effective_at,
                    precision=self.effective_precision,
                    label="transaction fact effective_at",
                ),
            )
        if not self.legs:
            raise ValueError("transaction fact must include at least one leg")
        counts_by_kind, signed_counts, leg_ids_by_kind = fact_leg_counts(
            self.legs, self.leg_policy
        )
        validate_fact_counts(self.leg_policy, counts_by_kind, signed_counts)
        validate_fact_leg_attribution(self.legs, leg_ids_by_kind)

    @property
    def economic_kind(self) -> EconomicKind:
        return self.semantics.economic_kind

    @property
    def accounting_intent_hint(self) -> AccountingIntentHint:
        return self.semantics.accounting_intent_hint

    @property
    def tax_treatment_hint(self) -> TaxTreatmentHint:
        return self.semantics.tax_treatment_hint

    @property
    def projection_hint(self) -> ProjectionHint | None:
        return self.semantics.projection_hint

    def to_row(self) -> dict[str, str]:
        return {
            "schema_version": str(FACT_SCHEMA_VERSION),
            "fact_id": str(self.fact_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "timestamp": format_timestamp(self.timestamp),
            "effective_at": (
                ""
                if self.effective_at is None or self.effective_precision is None
                else format_temporal_value(
                    self.effective_at,
                    precision=self.effective_precision,
                    label="transaction fact effective_at",
                )
            ),
            "effective_precision": ""
            if self.effective_precision is None
            else self.effective_precision.value,
            "location_id": str(self.location_id),
            "economic_kind": self.economic_kind.value,
            "projection_hint": ""
            if self.projection_hint is None
            else self.projection_hint.value,
            "accounting_intent_hint": self.accounting_intent_hint.value,
            "tax_treatment_hint": self.tax_treatment_hint.value,
            "description": self.description,
            "provider_operation_key": self.provider_operation_key,
            "operation_group_id": self.operation_group_id,
            "tx_hash": self.tx_hash or "",
            "raw_file": self.raw_file,
            "raw_row_ref": self.raw_row_ref,
            "confidence": self.confidence,
            "status": self.status,
            "legs": _json_text(_legs_json(self.legs)),
            "leg_policy": _json_text(_leg_policy_json(self.leg_policy)),
        }


def _legs_json(legs: tuple[EconomicLeg, ...]) -> list[dict[str, object]]:
    return [
        {
            "leg_id": leg.leg_id,
            "kind": leg.kind.value,
            "subtype": "" if leg.subtype is None else leg.subtype,
            "instrument_id": str(leg.instrument_id),
            "quantity": format_decimal(leg.quantity),
            "attributed_to_leg_id": ""
            if leg.attributed_to_leg_id is None
            else leg.attributed_to_leg_id,
            "location_id": "" if leg.location_id is None else str(leg.location_id),
        }
        for leg in legs
    ]


def _leg_policy_json(policy: FactLegPolicy) -> list[dict[str, object]]:
    return [
        {
            "kind": limit.kind.value,
            "min_count": limit.min_count,
            "max_count": limit.max_count,
            "min_positive_count": limit.min_positive_count,
            "max_positive_count": limit.max_positive_count,
            "min_negative_count": limit.min_negative_count,
            "max_negative_count": limit.max_negative_count,
        }
        for limit in sorted(policy.limits, key=lambda item: item.kind.value)
    ]


def _json_text(payload: list[dict[str, object]]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def _validate_leg_id(value: str, *, label: str) -> None:
    if not _LEG_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be lowercase snake_case")
