"""Filesystem fact row encoding and decoding helpers."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TypeVar, cast

from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import parse_temporal_precision
from tallylot.domain.transactions import (
    FACT_SCHEMA_VERSION,
    EconomicLeg,
    FactLegPolicy,
    FactSemantics,
    LegKind,
    LegShapeLimit,
    TransactionFact,
    parse_accounting_intent_hint,
    parse_economic_kind,
    parse_projection_hint,
    parse_tax_treatment_hint,
)
from tallylot.domain.types import AdapterId, LocationId, SourceId, TransactionId
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value, parse_timestamp

EnumT = TypeVar("EnumT")
JsonDict = dict[str, object]

FACT_HEADER = (
    "schema_version",
    "fact_id",
    "source",
    "adapter_id",
    "timestamp",
    "effective_at",
    "effective_precision",
    "location_id",
    "economic_kind",
    "projection_hint",
    "accounting_intent_hint",
    "tax_treatment_hint",
    "description",
    "provider_operation_key",
    "operation_group_id",
    "tx_hash",
    "raw_file",
    "raw_row_ref",
    "confidence",
    "status",
    "legs",
    "leg_policy",
)


def fact_from_row(row: dict[str, str]) -> TransactionFact:
    schema_version = row.get("schema_version", "")
    if schema_version != str(FACT_SCHEMA_VERSION):
        raise ValueError(
            f"unsupported fact schema_version: {schema_version or '<missing>'}; expected {FACT_SCHEMA_VERSION}"
        )
    effective_precision = (
        _required_enum(
            parse_temporal_precision(row.get("effective_precision", "")),
            "effective_precision",
        )
        if row.get("effective_at", "").strip()
        else None
    )
    return TransactionFact(
        fact_id=TransactionId(row["fact_id"]),
        source=SourceId(row["source"]),
        adapter_id=AdapterId(row["adapter_id"]),
        timestamp=parse_timestamp(row["timestamp"]),
        effective_at=(
            None
            if effective_precision is None
            else parse_temporal_value(row["effective_at"], precision=effective_precision)
        ),
        effective_precision=effective_precision,
        location_id=LocationId(row["location_id"]),
        leg_policy=_policy_from_text(row.get("leg_policy", "")),
        semantics=FactSemantics(
            economic_kind=_required_enum(parse_economic_kind(row["economic_kind"]), "economic_kind"),
            accounting_intent_hint=_required_enum(
                parse_accounting_intent_hint(row["accounting_intent_hint"]),
                "accounting_intent_hint",
            ),
            tax_treatment_hint=_required_enum(
                parse_tax_treatment_hint(row["tax_treatment_hint"]),
                "tax_treatment_hint",
            ),
            projection_hint=parse_projection_hint(row.get("projection_hint", "")),
        ),
        legs=_legs_from_text(row.get("legs", "")),
        description=row.get("description", ""),
        provider_operation_key=row.get("provider_operation_key", ""),
        operation_group_id=row.get("operation_group_id", ""),
        tx_hash=row.get("tx_hash") or None,
        raw_file=row.get("raw_file", ""),
        raw_row_ref=row.get("raw_row_ref", ""),
        confidence=row.get("confidence", "high"),
        status=row.get("status", "mapped"),
    )


def _legs_from_text(value: str) -> tuple[EconomicLeg, ...]:
    if not value:
        return ()
    raw_legs = _json_array(value, label="legs")
    legs: list[EconomicLeg] = []
    for raw_leg in raw_legs:
        legs.append(
            EconomicLeg(
                leg_id=_required_str(raw_leg, "leg_id"),
                kind=LegKind(_required_str(raw_leg, "kind")),
                instrument_id=InstrumentId(_required_str(raw_leg, "instrument_id")),
                quantity=_required_decimal(parse_decimal(_required_str(raw_leg, "quantity")), "leg.quantity"),
                subtype=_optional_str(raw_leg, "subtype"),
                attributed_to_leg_id=_optional_str(raw_leg, "attributed_to_leg_id"),
                location_id=(
                    None
                    if _optional_str(raw_leg, "location_id") is None
                    else LocationId(_required_str(raw_leg, "location_id"))
                ),
            )
        )
    return tuple(legs)


def _policy_from_text(value: str) -> FactLegPolicy:
    raw_limits = _json_array(value, label="leg_policy")
    return FactLegPolicy(
        limits=tuple(
            LegShapeLimit(
                kind=LegKind(_required_str(raw_limit, "kind")),
                min_count=_optional_int_value(raw_limit, "min_count") or 0,
                max_count=_required_int_value(raw_limit, "max_count"),
                min_positive_count=_optional_int_value(raw_limit, "min_positive_count"),
                max_positive_count=_optional_int_value(raw_limit, "max_positive_count"),
                min_negative_count=_optional_int_value(raw_limit, "min_negative_count"),
                max_negative_count=_optional_int_value(raw_limit, "max_negative_count"),
            )
            for raw_limit in raw_limits
        )
    )


def _json_array(value: str, *, label: str) -> list[JsonDict]:
    try:
        payload: object = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON field {label}") from error
    if not isinstance(payload, list):
        raise ValueError(f"invalid JSON field {label}: expected array")
    normalized_payload: list[JsonDict] = []
    for item in cast(list[object], payload):
        if not isinstance(item, dict):
            raise ValueError(f"invalid JSON field {label}: expected array of objects")
        normalized_payload.append(cast(JsonDict, item))
    return normalized_payload


def _required_enum(enum_value: EnumT | None, label: str) -> EnumT:
    if enum_value is None:
        raise ValueError(f"missing required enum field: {label}")
    return enum_value


def _required_decimal(value: Decimal | None, label: str) -> Decimal:
    if value is None:
        raise ValueError(f"missing required decimal field: {label}")
    return value


def _required_str(raw: JsonDict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing required string field: {key}")
    return value


def _optional_str(raw: JsonDict, key: str) -> str | None:
    value = raw.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid string field: {key}")
    return value


def _required_int_value(raw: JsonDict, key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"missing required integer field: {key}")
    return value


def _optional_int_value(raw: JsonDict, key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"invalid integer field: {key}")
    return value
