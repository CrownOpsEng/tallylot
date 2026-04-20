"""Checkpoint models and helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from typing import cast

from tallylot.domain.assertion import (
    AssertionValue,
    SubjectRef,
    assertion_value_fingerprint,
    assertion_value_payload,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import JsonValue
from tallylot.domain.value_objects import format_temporal_value, require_utc_datetime

CHECKPOINT_SCHEMA_VERSION = 1


def _json_text(payload: JsonValue) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _stable_id(components: JsonValue) -> str:
    return _json_text(components)


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
    raise ValueError(f"unsupported JSON value in checkpoint payload: {value!r}")


def _subject_ref_payload(subject_ref: SubjectRef) -> list[JsonValue]:
    kind, key = subject_ref
    return [kind, _json_ready(key)]


class CheckpointAssertionValueKind(StrEnum):
    POSITION_QUANTITY = "position_quantity"


class CheckpointAssertionTrustLevel(StrEnum):
    FILING_READY = "filing_ready"
    ANALYSIS_READY = "analysis_ready"


class CheckpointAssertionBasis(StrEnum):
    DOCUMENT_SUPPORT = "document_support"
    RECONCILED_CONTINUITY = "reconciled_continuity"


class CheckpointAssertionSupportShape(StrEnum):
    DOCUMENT_OBSERVATION = "document_observation"


class CheckpointAssertionContinuityKind(StrEnum):
    OBSERVED_CONTINUITY = "observed_continuity"
    RECONCILED_ROLLFORWARD = "reconciled_rollforward"


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    as_of: datetime
    assertion_ids: tuple[str, ...]
    proposal_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="checkpoint record as_of"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint record as_of",
            ),
            "assertion_ids": list(self.assertion_ids),
            "proposal_refs": list(sorted(self.proposal_refs)),
        }


@dataclass(frozen=True)
class CheckpointAssertionRecord:
    assertion_id: str
    checkpoint_id: str
    subject_ref: SubjectRef
    kind: CheckpointAssertionValueKind
    as_of: datetime
    accepted_value: AssertionValue
    trust_level: CheckpointAssertionTrustLevel
    basis: CheckpointAssertionBasis
    support_shape: CheckpointAssertionSupportShape
    continuity_kind: CheckpointAssertionContinuityKind

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="checkpoint assertion as_of"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "assertion_id": self.assertion_id,
            "checkpoint_id": self.checkpoint_id,
            "subject_ref": _subject_ref_payload(self.subject_ref),
            "kind": self.kind.value,
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint assertion as_of",
            ),
            "accepted_value": assertion_value_payload(self.accepted_value),
            "trust_level": self.trust_level.value,
            "basis": self.basis.value,
            "support_shape": self.support_shape.value,
            "continuity_kind": self.continuity_kind.value,
        }


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    reconciliation_state_refs: tuple[str, ...]
    as_of: datetime
    checkpoint_records: tuple[CheckpointRecord, ...]
    checkpoint_assertion_records: tuple[CheckpointAssertionRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="checkpoint as_of"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "reconciliation_state_refs": list(sorted(self.reconciliation_state_refs)),
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint as_of",
            ),
            "checkpoint_records": [
                record.to_payload() for record in self.checkpoint_records
            ],
            "checkpoint_assertion_records": [
                record.to_payload()
                for record in canonical_checkpoint_assertion_records(
                    self.checkpoint_assertion_records
                )
            ],
        }


def stable_checkpoint_id(
    *, reconciliation_state_refs: tuple[str, ...], as_of: datetime
) -> str:
    return _stable_id(
        [
            list(sorted(reconciliation_state_refs)),
            format_temporal_value(
                as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint as_of",
            ),
        ]
    )


def stable_checkpoint_assertion_id(
    *,
    kind: CheckpointAssertionValueKind,
    as_of: datetime,
    subject_ref: SubjectRef,
    accepted_value: AssertionValue,
) -> str:
    return _stable_id(
        [
            kind.value,
            format_temporal_value(
                as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint assertion as_of",
            ),
            _subject_ref_payload(subject_ref),
            assertion_value_fingerprint(accepted_value),
        ]
    )


def canonical_checkpoint_assertion_records(
    records: tuple[CheckpointAssertionRecord, ...],
) -> tuple[CheckpointAssertionRecord, ...]:
    return tuple(sorted(records, key=lambda item: (item.as_of, item.assertion_id)))


def checkpoint_fingerprint(checkpoint: Checkpoint) -> str:
    return sha256(_json_text(checkpoint.to_payload()).encode("utf-8")).hexdigest()
