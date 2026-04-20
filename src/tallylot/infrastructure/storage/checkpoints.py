"""Filesystem Checkpoint repository."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from tallylot.domain.assertion import (
    LocationValue,
    MoneyValue,
    OwnerValue,
    QuantityValue,
)
from tallylot.domain.checkpoint import (
    CHECKPOINT_SCHEMA_VERSION,
    Checkpoint,
    CheckpointAssertionBasis,
    CheckpointAssertionContinuityKind,
    CheckpointAssertionRecord,
    CheckpointAssertionSupportShape,
    CheckpointAssertionTrustLevel,
    CheckpointAssertionValueKind,
    CheckpointRecord,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


class FilesystemCheckpointRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def write_checkpoint(self, path: Path, checkpoint: Checkpoint) -> None:
        self._artifacts.write_json(path, checkpoint.to_payload())

    def read_checkpoint(self, path: Path) -> Checkpoint:
        payload = _required_dict(
            json.loads(path.read_text(encoding="utf-8")), "payload"
        )
        schema_version = payload.get("schema_version")
        if schema_version != CHECKPOINT_SCHEMA_VERSION:
            rendered = "<missing>" if schema_version in (None, "") else schema_version
            raise ValueError(
                f"unsupported checkpoint schema_version: {rendered}; expected {CHECKPOINT_SCHEMA_VERSION}"
            )
        return Checkpoint(
            checkpoint_id=_required_text(payload, "checkpoint_id"),
            reconciliation_state_refs=_required_text_tuple(
                payload, "reconciliation_state_refs"
            ),
            as_of=_required_temporal(payload, "as_of"),
            checkpoint_records=tuple(
                _checkpoint_record_from_payload(item)
                for item in _required_list(payload, "checkpoint_records")
            ),
            checkpoint_assertion_records=tuple(
                _checkpoint_assertion_from_payload(item)
                for item in _required_list(payload, "checkpoint_assertion_records")
            ),
        )


def _checkpoint_record_from_payload(payload: object) -> CheckpointRecord:
    raw = _required_dict(payload, "checkpoint record")
    return CheckpointRecord(
        checkpoint_id=_required_text(raw, "checkpoint_id"),
        as_of=_required_temporal(raw, "as_of"),
        assertion_ids=_required_text_tuple(raw, "assertion_ids"),
        proposal_refs=_required_text_tuple(raw, "proposal_refs"),
    )


def _checkpoint_assertion_from_payload(payload: object) -> CheckpointAssertionRecord:
    raw = _required_dict(payload, "checkpoint assertion")
    return CheckpointAssertionRecord(
        assertion_id=_required_text(raw, "assertion_id"),
        checkpoint_id=_required_text(raw, "checkpoint_id"),
        subject_ref=_required_subject_ref(raw, "subject_ref"),
        kind=CheckpointAssertionValueKind(_required_text(raw, "kind")),
        as_of=_required_temporal(raw, "as_of"),
        accepted_value=_required_assertion_value(raw, "accepted_value"),
        trust_level=CheckpointAssertionTrustLevel(_required_text(raw, "trust_level")),
        basis=CheckpointAssertionBasis(_required_text(raw, "basis")),
        support_shape=CheckpointAssertionSupportShape(
            _required_text(raw, "support_shape")
        ),
        continuity_kind=CheckpointAssertionContinuityKind(
            _required_text(raw, "continuity_kind")
        ),
    )


def _required_assertion_value(
    payload: dict[str, object], key: str
) -> QuantityValue | MoneyValue | OwnerValue | LocationValue:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError("invalid checkpoint assertion value: expected array")
    parts = cast(list[object], value)
    if len(parts) != 2 or not isinstance(parts[0], str):
        raise ValueError("invalid checkpoint assertion value: expected tagged array")
    kind = parts[0]
    items = _required_list_object(parts[1], "checkpoint assertion value")
    if kind == "quantity":
        return QuantityValue(
            quantity=_required_decimal_text(
                _required_list_item(items, 0, "quantity amount")
            ),
            subject_ref=_subject_ref_from_payload(
                _required_list_item(items, 1, "quantity subject_ref")
            ),
        )
    if kind == "money":
        currency = _required_list_item(items, 1, "money currency")
        if not isinstance(currency, str):
            raise ValueError("invalid checkpoint money value")
        return MoneyValue(
            amount=_required_decimal_text(
                _required_list_item(items, 0, "money amount")
            ),
            currency=currency,
        )
    if kind == "owner":
        return OwnerValue(
            legal_owner_ref=_optional_list_text(items, 0),
            beneficial_owner_ref=_optional_list_text(items, 1),
            counterparty_ref=_optional_list_text(items, 2),
        )
    if kind == "location":
        location_ref = _required_list_item(items, 0, "location ref")
        if not isinstance(location_ref, str):
            raise ValueError("invalid checkpoint location value")
        return LocationValue(location_ref=location_ref)
    raise ValueError(f"invalid checkpoint assertion value kind: {kind}")


def _optional_list_text(items: list[object], index: int) -> str:
    value = items[index] if index < len(items) else ""
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError("invalid checkpoint owner value")
    return value


def _required_list_item(items: list[object], index: int, label: str) -> object:
    if index >= len(items):
        raise ValueError(f"invalid checkpoint assertion value: missing {label}")
    return items[index]


def _required_list_object(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"invalid {label}: expected array")
    return cast(list[object], value)


def _required_subject_ref(
    payload: dict[str, object], key: str
) -> tuple[str, tuple[object, ...]]:
    return _subject_ref_from_payload(payload.get(key))


def _subject_ref_from_payload(value: object) -> tuple[str, tuple[object, ...]]:
    if not isinstance(value, list):
        raise ValueError("invalid checkpoint subject_ref: expected array")
    parts = cast(list[object], value)
    if len(parts) != 2 or not isinstance(parts[0], str):
        raise ValueError("invalid checkpoint subject_ref: expected array")
    raw_key = parts[1]
    if not isinstance(raw_key, list):
        raise ValueError("invalid checkpoint subject_ref: expected key array")
    return (parts[0], _tupled(cast(list[object], raw_key)))


def _tupled(value: list[object]) -> tuple[object, ...]:
    return tuple(_tupled_item(item) for item in value)


def _tupled_item(value: object) -> object:
    if isinstance(value, list):
        return _tupled(cast(list[object], value))
    return value


def _required_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid checkpoint {label}: expected object")
    raw = cast(dict[object, object], value)
    return {str(key): item for key, item in raw.items()}


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid checkpoint {key}: expected array")
    return cast(list[object], value)


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or value == "":
        raise ValueError(f"invalid checkpoint {key}: expected non-empty string")
    return value


def _required_text_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid checkpoint {key}: expected array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid checkpoint {key}: expected string array")
    return tuple(cast(list[str], items))


def _required_temporal(payload: dict[str, object], key: str) -> datetime:
    return parse_temporal_value(
        _required_text(payload, key), precision=TemporalPrecision.TIMESTAMP
    )


def _required_decimal_text(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("invalid checkpoint decimal value")
    parsed = parse_decimal(value)
    if parsed is None:
        raise ValueError("invalid checkpoint decimal value")
    return parsed
