"""Filesystem ClaimSet repository."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from tallylot.domain.claim import (
    CLAIM_SET_SCHEMA_VERSION,
    ClaimBundleDecisionBasis,
    ClaimBundleDecisionOutcome,
    ClaimBundleDecisionRecord,
    ClaimBundleRecord,
    ClaimKind,
    ClaimLegSpec,
    ClaimRecord,
    ClaimRecordStatus,
    ClaimSet,
)
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


class FilesystemClaimSetRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def write_claim_set(self, path: Path, claim_set: ClaimSet) -> None:
        self._artifacts.write_json(path, claim_set.to_payload())

    def read_claim_set(self, path: Path) -> ClaimSet:
        payload = _required_dict(
            json.loads(path.read_text(encoding="utf-8")), "payload"
        )
        schema_version = payload.get("schema_version")
        if schema_version != CLAIM_SET_SCHEMA_VERSION:
            rendered = "<missing>" if schema_version in (None, "") else schema_version
            raise ValueError(
                "unsupported claim set schema_version: "
                f"{rendered}; expected {CLAIM_SET_SCHEMA_VERSION}"
            )
        return ClaimSet(
            claim_set_id=_required_text(payload, "claim_set_id"),
            evidence_set_ref=_required_text(payload, "evidence_set_ref"),
            emitter_id=_required_text(payload, "emitter_id"),
            claim_records=tuple(
                _claim_record_from_payload(item)
                for item in _required_list(payload, "claim_records")
            ),
            claim_bundle_records=tuple(
                _claim_bundle_from_payload(item)
                for item in _required_list(payload, "claim_bundle_records")
            ),
            claim_bundle_decision_records=tuple(
                _claim_bundle_decision_from_payload(item)
                for item in _required_list(payload, "claim_bundle_decision_records")
            ),
        )


def _claim_record_from_payload(payload: object) -> ClaimRecord:
    raw = _required_dict(payload, "claim")
    precision = parse_temporal_precision(_optional_text(raw, "precision"))
    leg_specs = tuple(
        ClaimLegSpec(
            slot=int(_required_number(spec, "slot")),
            role=_required_text(spec, "role"),
            quantity=_required_decimal(spec, "quantity"),
            instrument_claim_refs=_required_text_tuple(spec, "instrument_claim_refs"),
            location_claim_ref=_required_text(spec, "location_claim_ref"),
            subtype=_required_text(spec, "subtype"),
            attributed_to_slot=(
                None
                if spec.get("attributed_to_slot") is None
                else int(_required_number(spec, "attributed_to_slot"))
            ),
        )
        for spec in (
            _required_dict(item, "claim leg spec")
            for item in _required_list(raw, "leg_specs", default=[])
        )
    )
    return ClaimRecord(
        claim_set_id=_required_text(raw, "claim_set_id"),
        scope_id=_required_text(raw, "scope_id"),
        bundle_id=_required_text(raw, "bundle_id"),
        claim_id=_required_text(raw, "claim_id"),
        kind=ClaimKind(_required_text(raw, "kind")),
        status=ClaimRecordStatus(_required_text(raw, "status")),
        key=_required_text_tuple(raw, "key"),
        member_refs=_required_text_tuple(raw, "member_refs"),
        observation_refs=_required_text_tuple(raw, "observation_refs"),
        effective_at=_optional_temporal(raw, "effective_at", precision=precision),
        precision=precision,
        provenance_refs=_required_text_tuple(raw, "provenance_refs"),
        activity_label=_optional_text(raw, "activity_label"),
        location_claim_ref=_optional_text(raw, "location_claim_ref"),
        leg_specs=leg_specs,
        instrument_claim_refs=_required_text_tuple(
            raw, "instrument_claim_refs", default=()
        ),
        balance_kind=_optional_text(raw, "balance_kind"),
        quantity=parse_decimal(_optional_text(raw, "quantity")),
        observed_at=_optional_temporal(raw, "observed_at", precision=precision),
        scheme=_optional_text(raw, "scheme"),
        value=_optional_text(raw, "value"),
        venue=_optional_text(raw, "venue"),
        instrument_kind=_optional_text(raw, "instrument_kind"),
        name=_optional_text(raw, "name"),
        location_ref=_optional_text(raw, "location_ref"),
        location_group_label=_optional_text(raw, "location_group_label"),
        location_label=_optional_text(raw, "location_label"),
        beneficial_owner_ref=_optional_text(raw, "beneficial_owner_ref"),
        purpose=_optional_text(raw, "purpose"),
        amount=parse_decimal(_optional_text(raw, "amount")),
        currency=_optional_text(raw, "currency"),
        valued_at=_optional_temporal(raw, "valued_at", precision=precision),
    )


def _claim_bundle_from_payload(payload: object) -> ClaimBundleRecord:
    raw = _required_dict(payload, "claim bundle")
    return ClaimBundleRecord(
        claim_set_id=_required_text(raw, "claim_set_id"),
        scope_id=_required_text(raw, "scope_id"),
        bundle_id=_required_text(raw, "bundle_id"),
        key=_required_text(raw, "key"),
        scope_key=_required_text_tuple(raw, "scope_key"),
        claim_refs=_required_text_tuple(raw, "claim_refs"),
    )


def _claim_bundle_decision_from_payload(payload: object) -> ClaimBundleDecisionRecord:
    raw = _required_dict(payload, "claim bundle decision")
    return ClaimBundleDecisionRecord(
        claim_set_id=_required_text(raw, "claim_set_id"),
        scope_id=_required_text(raw, "scope_id"),
        decision_id=_required_text(raw, "decision_id"),
        outcome=ClaimBundleDecisionOutcome(_required_text(raw, "outcome")),
        accepted_bundle_ref=_optional_text(raw, "accepted_bundle_ref"),
        rejected_bundle_refs=_required_text_tuple(
            raw, "rejected_bundle_refs", default=()
        ),
        deferred_bundle_refs=_required_text_tuple(
            raw, "deferred_bundle_refs", default=()
        ),
        basis=ClaimBundleDecisionBasis(_required_text(raw, "basis")),
        blocking_gap_refs=_required_text_tuple(raw, "blocking_gap_refs", default=()),
    )


def _required_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid claim set {label}: expected object")
    raw = cast(dict[object, object], value)
    return {str(raw_key): raw_value for raw_key, raw_value in raw.items()}


def _required_list(
    payload: dict[str, object], key: str, *, default: list[object] | None = None
) -> list[object]:
    value = payload.get(key, default)
    if not isinstance(value, list):
        raise ValueError(f"invalid claim set {key}: expected array")
    return cast(list[object], value)


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or value == "":
        raise ValueError(f"invalid claim set {key}: expected non-empty string")
    return value


def _optional_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"invalid claim set {key}: expected string")
    return value


def _required_text_tuple(
    payload: dict[str, object], key: str, *, default: tuple[str, ...] | None = None
) -> tuple[str, ...]:
    value = payload.get(key, list(default or ()))
    if not isinstance(value, list):
        raise ValueError(f"invalid claim set {key}: expected array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid claim set {key}: expected string array")
    return tuple(cast(list[str], items))


def _required_number(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"invalid claim set {key}: expected integer")
    return value


def _required_decimal(payload: dict[str, object], key: str) -> Decimal:
    value = parse_decimal(_required_text(payload, key))
    if value is None:
        raise ValueError(f"invalid claim set {key}: expected decimal")
    return value


def _optional_temporal(
    payload: dict[str, object], key: str, *, precision: TemporalPrecision | None
) -> datetime | None:
    text = _optional_text(payload, key)
    if not text:
        return None
    if precision is None:
        raise ValueError(
            f"invalid claim set {key}: precision is required when a temporal value is present"
        )
    return parse_temporal_value(text, precision=precision)
