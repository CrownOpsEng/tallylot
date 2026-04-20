"""EconomicFacts models and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
from typing import cast

from tallylot.domain.assertion import SubjectRef
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    require_utc_datetime,
)

ECONOMIC_FACTS_SCHEMA_VERSION = 1


def _json_text(payload: JsonValue) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _stable_id(components: JsonValue) -> str:
    return _json_text(components)


def _stable_product_id(components: JsonValue) -> str:
    return sha256(_json_text(components).encode("utf-8")).hexdigest()


def _subject_ref_payload(subject_ref: SubjectRef) -> list[JsonValue]:
    kind, key = subject_ref
    return [kind, _json_ready(key)]


def _json_ready(value: object) -> JsonValue:
    if isinstance(value, tuple):
        tuple_items = cast(tuple[object, ...], value)
        return [_json_ready(item) for item in tuple_items]
    if isinstance(value, list):
        list_items = cast(list[object], value)
        return [_json_ready(item) for item in list_items]
    if isinstance(value, dict):
        dict_items = cast(dict[object, object], value)
        return {str(key): _json_ready(item) for key, item in dict_items.items()}
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise ValueError(f"unsupported JSON value in economic payload: {value!r}")


class EconomicEventKind(StrEnum):
    ASSET_MOVEMENT = "asset_movement"
    CASH_MOVEMENT = "cash_movement"
    OBLIGATION_OR_RIGHT = "obligation_or_right"
    SETTLEMENT = "settlement"
    COLLATERAL_CHANGE = "collateral_change"
    FINANCING_FLOW = "financing_flow"
    FEE_OR_REBATE = "fee_or_rebate"
    WITHHOLDING = "withholding"
    LIFECYCLE_RESTRUCTURE = "lifecycle_restructure"
    CORRECTION = "correction"


class SettlementStatus(StrEnum):
    SETTLED = "settled"


class LifecycleEvent(StrEnum):
    CREATED = "created"
    MIGRATED = "migrated"


class EconomicLegRole(StrEnum):
    HOLDING_CHANGE = "holding_change"
    CASH_CHANGE = "cash_change"
    OBLIGATION_CHANGE = "obligation_change"
    SETTLEMENT_CHANGE = "settlement_change"
    COLLATERAL_CHANGE = "collateral_change"
    FINANCING_CHANGE = "financing_change"
    FEE = "fee"
    REBATE = "rebate"
    WITHHOLDING = "withholding"


@dataclass(frozen=True)
class EconomicEventRecord:
    event_id: str
    claim_bundle_id: str
    claim_bundle_decision_id: str
    kind: EconomicEventKind
    effective_at: datetime
    recorded_at: datetime
    settlement_status: SettlementStatus
    lifecycle_event: LifecycleEvent
    legal_owner_ref: str = ""
    beneficial_owner_ref: str = ""
    counterparty_ref: str = ""
    supersedes_event_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "effective_at",
            require_utc_datetime(
                self.effective_at, label="economic event effective_at"
            ),
        )
        object.__setattr__(
            self,
            "recorded_at",
            require_utc_datetime(self.recorded_at, label="economic event recorded_at"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_id": self.event_id,
            "claim_bundle_id": self.claim_bundle_id,
            "claim_bundle_decision_id": self.claim_bundle_decision_id,
            "kind": self.kind.value,
            "effective_at": format_temporal_value(
                self.effective_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="economic event effective_at",
            ),
            "recorded_at": format_temporal_value(
                self.recorded_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="economic event recorded_at",
            ),
            "settlement_status": self.settlement_status.value,
            "lifecycle_event": self.lifecycle_event.value,
            "legal_owner_ref": self.legal_owner_ref,
            "beneficial_owner_ref": self.beneficial_owner_ref,
            "counterparty_ref": self.counterparty_ref,
            "supersedes_event_id": self.supersedes_event_id,
        }


@dataclass(frozen=True)
class EconomicLegRecord:
    leg_id: str
    event_id: str
    role: EconomicLegRole
    subject_ref: SubjectRef
    instrument_ref: tuple[str, ...]
    location_ref: tuple[str, ...]
    quantity: Decimal
    valuation_ref: str = ""

    def __post_init__(self) -> None:
        if not self.instrument_ref:
            raise ValueError("economic leg instrument_ref must not be empty")
        if not self.location_ref:
            raise ValueError("economic leg location_ref must not be empty")
        if self.quantity == Decimal("0"):
            raise ValueError("economic leg quantity must not be zero")

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "leg_id": self.leg_id,
            "event_id": self.event_id,
            "role": self.role.value,
            "subject_ref": _subject_ref_payload(self.subject_ref),
            "instrument_ref": list(self.instrument_ref),
            "location_ref": list(self.location_ref),
            "quantity": format_decimal(self.quantity),
            "valuation_ref": self.valuation_ref,
        }


@dataclass(frozen=True)
class ValuationRecord:
    valuation_id: str
    origin_ref: tuple[str, str]
    purpose: str
    amount: Decimal
    currency: str
    valued_at: datetime
    precision: TemporalPrecision
    provenance_refs: tuple[str, ...]
    confidence: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "valued_at",
            require_utc_datetime(self.valued_at, label="valuation valued_at"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "valuation_id": self.valuation_id,
            "origin_ref": [self.origin_ref[0], self.origin_ref[1]],
            "purpose": self.purpose,
            "amount": format_decimal(self.amount),
            "currency": self.currency,
            "valued_at": format_temporal_value(
                self.valued_at,
                precision=self.precision,
                label="valuation valued_at",
            ),
            "precision": self.precision.value,
            "provenance_refs": list(sorted(self.provenance_refs)),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class EconomicFacts:
    economic_facts_id: str
    claim_set_refs: tuple[str, ...]
    economic_event_records: tuple[EconomicEventRecord, ...]
    economic_leg_records: tuple[EconomicLegRecord, ...]
    valuation_records: tuple[ValuationRecord, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "economic_facts_id": self.economic_facts_id,
            "schema_version": ECONOMIC_FACTS_SCHEMA_VERSION,
            "claim_set_refs": list(self.claim_set_refs),
            "economic_event_records": [
                record.to_payload()
                for record in canonical_economic_event_records(
                    self.economic_event_records
                )
            ],
            "economic_leg_records": [
                record.to_payload()
                for record in canonical_economic_leg_records(self.economic_leg_records)
            ],
            "valuation_records": [
                record.to_payload()
                for record in canonical_valuation_records(self.valuation_records)
            ],
        }


def stable_economic_facts_id(claim_set_refs: tuple[str, ...]) -> str:
    return _stable_product_id([*sorted(claim_set_refs)])


def stable_event_id(claim_bundle_id: str, event_slot: int) -> str:
    return _stable_id([claim_bundle_id, event_slot])


def stable_leg_id(
    event_id: str,
    role: EconomicLegRole,
    subject_ref: SubjectRef,
    leg_slot: int,
) -> str:
    return _stable_id(
        [event_id, role.value, _subject_ref_payload(subject_ref), leg_slot]
    )


def canonical_economic_event_records(
    records: tuple[EconomicEventRecord, ...],
) -> tuple[EconomicEventRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (item.effective_at, item.recorded_at, item.event_id),
        )
    )


def canonical_economic_leg_records(
    records: tuple[EconomicLegRecord, ...],
) -> tuple[EconomicLegRecord, ...]:
    return tuple(
        sorted(
            records,
            key=lambda item: (item.event_id, _leg_slot(item.leg_id), item.leg_id),
        )
    )


def canonical_valuation_records(
    records: tuple[ValuationRecord, ...],
) -> tuple[ValuationRecord, ...]:
    return tuple(
        sorted(
            records, key=lambda item: (item.purpose, item.valued_at, item.valuation_id)
        )
    )


def economic_facts_fingerprint(economic_facts: EconomicFacts) -> str:
    return sha256(_json_text(economic_facts.to_payload()).encode("utf-8")).hexdigest()


def _leg_slot(leg_id: str) -> int:
    payload = cast(list[object], json.loads(leg_id))
    slot = payload[3]
    if not isinstance(slot, int):
        raise ValueError(f"invalid economic leg_id: {leg_id}")
    return slot
