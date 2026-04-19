"""Filesystem EvidenceSet repository."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import cast

from tallylot.domain.evidence import (
    EVIDENCE_SET_SCHEMA_VERSION,
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceObservationKind,
    EvidenceObservationRecord,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
    EvidenceSet,
)
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


class FilesystemEvidenceSetRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def write_evidence_set(self, path: Path, evidence_set: EvidenceSet) -> None:
        self._artifacts.write_json(path, evidence_set.to_payload())

    def read_evidence_set(self, path: Path) -> EvidenceSet:
        payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        schema_version = payload.get("schema_version")
        if schema_version != EVIDENCE_SET_SCHEMA_VERSION:
            rendered = "<missing>" if schema_version in (None, "") else schema_version
            raise ValueError(
                "unsupported evidence set schema_version: "
                f"{rendered}; expected {EVIDENCE_SET_SCHEMA_VERSION}"
            )
        selections = tuple(
            _selection_from_payload(item)
            for item in _required_list(payload, "evidence_selection_records")
        )
        members = tuple(
            _member_from_payload(item)
            for item in _required_list(payload, "evidence_member_records")
        )
        observations = tuple(
            _observation_from_payload(item)
            for item in _required_list(payload, "evidence_observation_records")
        )
        return EvidenceSet(
            evidence_set_id=_required_text(payload, "evidence_set_id"),
            selection_fingerprint=_required_text(payload, "selection_fingerprint"),
            capture_manifest_fingerprint=_required_text(
                payload, "capture_manifest_fingerprint"
            ),
            evidence_selection_records=selections,
            evidence_member_records=members,
            evidence_observation_records=observations,
        )


def _selection_from_payload(payload: object) -> EvidenceSelectionRecord:
    raw = _required_dict(payload, "selection")
    return EvidenceSelectionRecord(
        evidence_set_id=_required_text(raw, "evidence_set_id"),
        selection_id=_required_text(raw, "selection_id"),
        key=_required_text_tuple(raw, "key"),
        fingerprint=_required_text(raw, "fingerprint"),
        basis=EvidenceSelectionBasis(_required_text(raw, "basis")),
        blocking_gap_refs=_required_text_tuple(raw, "blocking_gap_refs"),
    )


def _member_from_payload(payload: object) -> EvidenceMemberRecord:
    raw = _required_dict(payload, "member")
    return EvidenceMemberRecord(
        evidence_set_id=_required_text(raw, "evidence_set_id"),
        selection_id=_required_text(raw, "selection_id"),
        member_id=_required_text(raw, "member_id"),
        source_slug=_required_text(raw, "source_slug"),
        adapter_id=_required_text(raw, "adapter_id"),
        capture_uid=_required_text(raw, "capture_uid"),
        kind=EvidenceMemberKind(_required_text(raw, "kind")),
        locator=_required_text_tuple(raw, "locator"),
        status=EvidenceMemberStatus(_required_text(raw, "status")),
        capture_manifest_fingerprint=_required_text(
            raw, "capture_manifest_fingerprint"
        ),
    )


def _observation_from_payload(payload: object) -> EvidenceObservationRecord:
    raw = _required_dict(payload, "observation")
    precision = parse_temporal_precision(_optional_text(raw, "precision"))
    document_effective_precision = parse_temporal_precision(
        _optional_text(raw, "document_effective_precision")
    )
    statement_as_of_precision = parse_temporal_precision(
        _optional_text(raw, "statement_as_of_precision")
    )
    return EvidenceObservationRecord(
        evidence_set_id=_required_text(raw, "evidence_set_id"),
        member_id=_required_text(raw, "member_id"),
        observation_id=_required_text(raw, "observation_id"),
        kind=EvidenceObservationKind(_required_text(raw, "kind")),
        key=_required_text_tuple(raw, "key"),
        observed_at=_optional_temporal(raw, "observed_at", precision=precision),
        precision=precision,
        provenance_refs=_required_ref_tuples(raw, "provenance_refs"),
        statement_kind=_optional_text(raw, "statement_kind"),
        document_effective_at=_optional_temporal(
            raw,
            "document_effective_at",
            precision=document_effective_precision,
        ),
        document_effective_precision=document_effective_precision,
        statement_as_of=_optional_temporal(
            raw,
            "statement_as_of",
            precision=statement_as_of_precision,
        ),
        statement_as_of_precision=statement_as_of_precision,
        location_group_label=_optional_text(raw, "location_group_label"),
        location_label=_optional_text(raw, "location_label"),
        balance_kind=_optional_text(raw, "balance_kind"),
        instrument_symbol=_optional_text(raw, "instrument_symbol"),
        quantity=parse_decimal(_optional_text(raw, "quantity")),
        notes=_optional_text(raw, "notes"),
        staked_quantity_text=_optional_text(raw, "staked_quantity_text"),
        value_amount_text=_optional_text(raw, "value_amount_text"),
        value_currency=_optional_text(raw, "value_currency"),
        price_amount_text=_optional_text(raw, "price_amount_text"),
        price_currency=_optional_text(raw, "price_currency"),
    )


def _required_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid evidence set {label}: expected object")
    raw = cast(dict[object, object], value)
    normalized: dict[str, object] = {}
    for raw_key, raw_value in raw.items():
        normalized[str(raw_key)] = raw_value
    return normalized


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid evidence set {key}: expected array")
    return cast(list[object], value)


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or value == "":
        raise ValueError(f"invalid evidence set {key}: expected non-empty string")
    return value


def _optional_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"invalid evidence set {key}: expected string")
    return value


def _required_text_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid evidence set {key}: expected array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid evidence set {key}: expected string array")
    return tuple(cast(list[str], items))


def _required_ref_tuples(
    payload: dict[str, object], key: str
) -> tuple[tuple[str, ...], ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid evidence set {key}: expected array")
    refs: list[tuple[str, ...]] = []
    for item in cast(list[object], value):
        if not isinstance(item, list):
            raise ValueError(
                f"invalid evidence set {key}: expected array of string arrays"
            )
        parts = cast(list[object], item)
        if not all(isinstance(part, str) for part in parts):
            raise ValueError(
                f"invalid evidence set {key}: expected array of string arrays"
            )
        refs.append(tuple(cast(list[str], parts)))
    return tuple(refs)


def _optional_temporal(
    payload: dict[str, object],
    key: str,
    *,
    precision: TemporalPrecision | None,
) -> datetime | None:
    text = _optional_text(payload, key)
    if not text:
        return None
    if precision is None:
        raise ValueError(
            f"invalid evidence set {key}: precision is required when a temporal value is present"
        )
    return parse_temporal_value(text, precision=precision)
