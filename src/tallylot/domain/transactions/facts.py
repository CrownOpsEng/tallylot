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
from tallylot.domain.value_objects import format_decimal, format_timestamp

from .classification import EconomicKind, JournalIntent, ProjectionType, TaxTreatmentCode

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
    max_in_count: int | None = None
    max_out_count: int | None = None

    def __post_init__(self) -> None:
        if self.max_count < 0:
            raise ValueError("leg shape limit max_count must be non-negative")
        if self.max_in_count is not None and self.max_in_count < 0:
            raise ValueError("leg shape limit max_in_count must be non-negative")
        if self.max_out_count is not None and self.max_out_count < 0:
            raise ValueError("leg shape limit max_out_count must be non-negative")
        if self.max_in_count is not None and self.max_in_count > self.max_count:
            raise ValueError("leg shape limit max_in_count must not exceed max_count")
        if self.max_out_count is not None and self.max_out_count > self.max_count:
            raise ValueError("leg shape limit max_out_count must not exceed max_count")


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
        if self.amount <= Decimal("0"):
            raise ValueError("fact leg amount must be greater than zero")
        if self.kind is LegKind.PRIMARY and self.attributed_to_direction is not None:
            raise ValueError("primary legs must not declare attributed_to_direction")
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
        if not self.legs:
            raise ValueError("transaction fact must include at least one leg")

        counts_by_kind: dict[LegKind, int] = {}
        directional_counts: dict[tuple[LegKind, FactDirection], int] = {}
        primary_legs_by_direction: dict[FactDirection, int] = {"in": 0, "out": 0}
        for leg in self.legs:
            limit = self.leg_policy.limit_for(leg.kind)
            if limit is None:
                raise ValueError(f"transaction fact leg kind {leg.kind.value} is not allowed by declared leg policy")
            counts_by_kind[leg.kind] = counts_by_kind.get(leg.kind, 0) + 1
            directional_key = (leg.kind, leg.direction)
            directional_counts[directional_key] = directional_counts.get(directional_key, 0) + 1
            if leg.kind is LegKind.PRIMARY:
                primary_legs_by_direction[leg.direction] += 1

        for limit in self.leg_policy.limits:
            total_count = counts_by_kind.get(limit.kind, 0)
            if total_count > limit.max_count:
                raise ValueError(f"transaction fact {limit.kind.value} legs exceed declared leg policy")
            inbound_count = directional_counts.get((limit.kind, "in"), 0)
            outbound_count = directional_counts.get((limit.kind, "out"), 0)
            if limit.max_in_count is not None and inbound_count > limit.max_in_count:
                raise ValueError(f"transaction fact inbound {limit.kind.value} legs exceed declared leg policy")
            if limit.max_out_count is not None and outbound_count > limit.max_out_count:
                raise ValueError(f"transaction fact outbound {limit.kind.value} legs exceed declared leg policy")

        for leg in self.legs:
            if leg.attributed_to_direction is None:
                continue
            if primary_legs_by_direction[leg.attributed_to_direction] != 1:
                raise ValueError(
                    "transaction fact attributed_to_direction must reference exactly one primary leg on that side"
                )

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
            "max_count": limit.max_count,
            "max_in_count": limit.max_in_count,
            "max_out_count": limit.max_out_count,
        }
        for limit in sorted(policy.limits, key=lambda item: item.kind.value)
    ]


def _json_text(payload: list[dict[str, object]]) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


SINGLE_PRIMARY_ACTIVITY_POLICY = FactLegPolicy(
    limits=(LegShapeLimit(kind=LegKind.PRIMARY, max_count=1, max_in_count=1, max_out_count=1),)
)
TWO_SIDED_PRIMARY_EXCHANGE_POLICY = FactLegPolicy(
    limits=(LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1),)
)
TWO_SIDED_PRIMARY_EXCHANGE_WITH_SINGLE_CHARGE_POLICY = FactLegPolicy(
    limits=(
        LegShapeLimit(kind=LegKind.PRIMARY, max_count=2, max_in_count=1, max_out_count=1),
        LegShapeLimit(kind=LegKind.CHARGE, max_count=1, max_in_count=0, max_out_count=1),
    )
)
