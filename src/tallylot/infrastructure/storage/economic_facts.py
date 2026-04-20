"""Filesystem EconomicFacts repository."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from tallylot.domain.economics import (
    ECONOMIC_FACTS_SCHEMA_VERSION,
    EconomicEventKind,
    EconomicEventRecord,
    EconomicFacts,
    EconomicLegRecord,
    EconomicLegRole,
    LifecycleEvent,
    SettlementStatus,
    ValuationRecord,
)
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


class FilesystemEconomicFactsRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def write_economic_facts(self, path: Path, economic_facts: EconomicFacts) -> None:
        self._artifacts.write_json(path, economic_facts.to_payload())

    def read_economic_facts(self, path: Path) -> EconomicFacts:
        payload = _required_dict(
            json.loads(path.read_text(encoding="utf-8")), "payload"
        )
        schema_version = payload.get("schema_version")
        if schema_version != ECONOMIC_FACTS_SCHEMA_VERSION:
            rendered = "<missing>" if schema_version in (None, "") else schema_version
            raise ValueError(
                "unsupported economic facts schema_version: "
                f"{rendered}; expected {ECONOMIC_FACTS_SCHEMA_VERSION}"
            )
        return EconomicFacts(
            economic_facts_id=_required_text(payload, "economic_facts_id"),
            claim_set_refs=_required_text_tuple(payload, "claim_set_refs"),
            economic_event_records=tuple(
                _economic_event_from_payload(item)
                for item in _required_list(payload, "economic_event_records")
            ),
            economic_leg_records=tuple(
                _economic_leg_from_payload(item)
                for item in _required_list(payload, "economic_leg_records")
            ),
            valuation_records=tuple(
                _valuation_from_payload(item)
                for item in _required_list(payload, "valuation_records")
            ),
        )


def _economic_event_from_payload(payload: object) -> EconomicEventRecord:
    raw = _required_dict(payload, "economic event")
    return EconomicEventRecord(
        event_id=_required_text(raw, "event_id"),
        claim_bundle_id=_required_text(raw, "claim_bundle_id"),
        claim_bundle_decision_id=_required_text(raw, "claim_bundle_decision_id"),
        kind=EconomicEventKind(_required_text(raw, "kind")),
        effective_at=_required_temporal(raw, "effective_at"),
        recorded_at=_required_temporal(raw, "recorded_at"),
        settlement_status=SettlementStatus(_required_text(raw, "settlement_status")),
        lifecycle_event=LifecycleEvent(_required_text(raw, "lifecycle_event")),
        legal_owner_ref=_optional_text(raw, "legal_owner_ref"),
        beneficial_owner_ref=_optional_text(raw, "beneficial_owner_ref"),
        counterparty_ref=_optional_text(raw, "counterparty_ref"),
        supersedes_event_id=_optional_text(raw, "supersedes_event_id"),
    )


def _economic_leg_from_payload(payload: object) -> EconomicLegRecord:
    raw = _required_dict(payload, "economic leg")
    subject_ref = _required_subject_ref(raw, "subject_ref")
    return EconomicLegRecord(
        leg_id=_required_text(raw, "leg_id"),
        event_id=_required_text(raw, "event_id"),
        role=EconomicLegRole(_required_text(raw, "role")),
        subject_ref=subject_ref,
        instrument_ref=_required_text_tuple(raw, "instrument_ref"),
        location_ref=_required_text_tuple(raw, "location_ref"),
        quantity=_required_decimal(raw, "quantity"),
        valuation_ref=_optional_text(raw, "valuation_ref"),
    )


def _valuation_from_payload(payload: object) -> ValuationRecord:
    raw = _required_dict(payload, "valuation")
    precision = parse_temporal_precision(_required_text(raw, "precision"))
    if precision is None:
        raise ValueError(
            "invalid economic facts precision: expected supported precision"
        )
    origin_ref = _required_text_tuple(raw, "origin_ref")
    if len(origin_ref) != 2:
        raise ValueError("invalid economic facts origin_ref: expected pair")
    return ValuationRecord(
        valuation_id=_required_text(raw, "valuation_id"),
        origin_ref=(origin_ref[0], origin_ref[1]),
        purpose=_required_text(raw, "purpose"),
        amount=_required_decimal(raw, "amount"),
        currency=_required_text(raw, "currency"),
        valued_at=_required_temporal(raw, "valued_at", precision=precision),
        precision=precision,
        provenance_refs=_required_text_tuple(raw, "provenance_refs"),
        confidence=_required_text(raw, "confidence"),
    )


def _required_subject_ref(
    payload: dict[str, object], key: str
) -> tuple[str, tuple[object, ...]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid economic facts {key}: expected subject ref array")
    parts = cast(list[object], value)
    if len(parts) != 2:
        raise ValueError(f"invalid economic facts {key}: expected subject ref array")
    kind = parts[0]
    raw_key = parts[1]
    if not isinstance(kind, str) or not isinstance(raw_key, list):
        raise ValueError(f"invalid economic facts {key}: expected subject ref array")
    return (kind, _tupled(cast(list[object], raw_key)))


def _tupled(value: list[object]) -> tuple[object, ...]:
    return tuple(
        _tupled(cast(list[object], item)) if isinstance(item, list) else item
        for item in value
    )


def _required_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid economic facts {label}: expected object")
    raw = cast(dict[object, object], value)
    return {str(raw_key): raw_value for raw_key, raw_value in raw.items()}


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid economic facts {key}: expected array")
    return cast(list[object], value)


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or value == "":
        raise ValueError(f"invalid economic facts {key}: expected non-empty string")
    return value


def _optional_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"invalid economic facts {key}: expected string")
    return value


def _required_text_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid economic facts {key}: expected array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid economic facts {key}: expected string array")
    return tuple(cast(list[str], items))


def _required_decimal(payload: dict[str, object], key: str) -> Decimal:
    value = parse_decimal(_required_text(payload, key))
    if value is None:
        raise ValueError(f"invalid economic facts {key}: expected decimal")
    return value


def _required_temporal(
    payload: dict[str, object],
    key: str,
    *,
    precision: TemporalPrecision = TemporalPrecision.TIMESTAMP,
) -> datetime:
    return parse_temporal_value(_required_text(payload, key), precision=precision)
