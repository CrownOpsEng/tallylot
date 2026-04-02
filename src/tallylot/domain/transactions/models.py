"""Provider-neutral transaction fact models."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from tallylot.domain.types import AdapterId, AssetSymbol, SourceId, TransactionId
from tallylot.domain.value_objects import format_decimal, format_timestamp, require_utc_datetime

from .classification import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode
from .validation import (
    fact_leg_counts,
    validate_directional_counts,
    validate_fact_counts,
    validate_fact_direction,
    validate_fact_leg_attribution,
    validate_non_negative_count,
)

FactDirection = Literal["in", "out"]
_LEG_SUBTYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


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
    max_in_count: int | None = None
    min_in_count: int | None = None
    max_out_count: int | None = None
    min_out_count: int | None = None

    def __post_init__(self) -> None:
        validate_non_negative_count(self.min_count, label="min_count")
        validate_non_negative_count(self.max_count, label="max_count")
        if self.min_count > self.max_count:
            raise ValueError("leg shape limit min_count must not exceed max_count")
        validate_directional_counts(self)


@dataclass(frozen=True)
class FactLegPolicy:
    limits: tuple[LegShapeLimit, ...]

    def __post_init__(self) -> None:
        if not self.limits:
            raise ValueError("fact leg policy must declare at least one supported leg kind")
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
class FactClassification:
    economic_kind: EconomicKind
    journal_intent: JournalIntent
    tax_treatment_code: TaxTreatmentCode
    projection_type: ProjectionType | None = None


@dataclass(frozen=True)
class EconomicLeg:
    direction: FactDirection
    kind: LegKind
    asset: AssetSymbol
    amount: Decimal
    subtype: str | None = None
    attributed_to_direction: FactDirection | None = None
    account: str = ""
    wallet: str = ""

    def __post_init__(self) -> None:
        validate_fact_direction(self.direction, label="fact leg direction")
        if self.amount <= Decimal("0"):
            raise ValueError("fact leg amount must be greater than zero")
        if self.kind is LegKind.PRIMARY and self.attributed_to_direction is not None:
            raise ValueError("primary legs must not declare attributed_to_direction")
        if self.attributed_to_direction is not None:
            validate_fact_direction(
                self.attributed_to_direction,
                label="fact leg attributed_to_direction",
            )
        if self.subtype is not None and not _LEG_SUBTYPE_PATTERN.fullmatch(self.subtype):
            raise ValueError("fact leg subtype must be lowercase snake_case")


@dataclass(frozen=True)
class TransactionFact:
    fact_id: TransactionId
    source: SourceId
    adapter_id: AdapterId
    timestamp: datetime
    account: str
    wallet: str
    classification: FactClassification
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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "timestamp",
            require_utc_datetime(self.timestamp, label="transaction fact timestamp"),
        )
        if not self.legs:
            raise ValueError("transaction fact must include at least one leg")
        counts_by_kind, directional_counts, primary_legs_by_direction = fact_leg_counts(self.legs, self.leg_policy)
        validate_fact_counts(self.leg_policy, counts_by_kind, directional_counts)
        validate_fact_leg_attribution(self.legs, primary_legs_by_direction)

    @property
    def economic_kind(self) -> EconomicKind:
        return self.classification.economic_kind

    @property
    def journal_intent(self) -> JournalIntent:
        return self.classification.journal_intent

    @property
    def tax_treatment_code(self) -> TaxTreatmentCode:
        return self.classification.tax_treatment_code

    @property
    def projection_type(self) -> ProjectionType | None:
        return self.classification.projection_type

    def to_row(self) -> dict[str, str]:
        return {
            "fact_id": str(self.fact_id),
            "source": str(self.source),
            "adapter_id": str(self.adapter_id),
            "timestamp": format_timestamp(self.timestamp),
            "account": self.account,
            "wallet": self.wallet,
            "economic_kind": self.economic_kind.value,
            "projection_type": "" if self.projection_type is None else self.projection_type.value,
            "journal_intent": self.journal_intent.value,
            "tax_treatment_code": self.tax_treatment_code.value,
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
            "direction": leg.direction,
            "kind": leg.kind.value,
            "subtype": "" if leg.subtype is None else leg.subtype,
            "asset": str(leg.asset),
            "amount": format_decimal(leg.amount),
            "attributed_to_direction": "" if leg.attributed_to_direction is None else leg.attributed_to_direction,
            "account": leg.account,
            "wallet": leg.wallet,
        }
        for leg in legs
    ]


def _leg_policy_json(policy: FactLegPolicy) -> list[dict[str, object]]:
    return [
        {
            "kind": limit.kind.value,
            "min_count": limit.min_count,
            "max_count": limit.max_count,
            "min_in_count": limit.min_in_count,
            "max_in_count": limit.max_in_count,
            "min_out_count": limit.min_out_count,
            "max_out_count": limit.max_out_count,
        }
        for limit in sorted(policy.limits, key=lambda item: item.kind.value)
    ]


def _json_text(payload: list[dict[str, object]]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
