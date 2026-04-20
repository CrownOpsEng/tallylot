"""ReconciliationState models and helpers."""

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

RECONCILIATION_STATE_SCHEMA_VERSION = 1


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
    raise ValueError(f"unsupported JSON value in reconciliation payload: {value!r}")


class ContinuitySegmentStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class BalanceTargetKind(StrEnum):
    EXACT_BALANCE = "exact_balance"


class BalanceTargetObservationStatus(StrEnum):
    OBSERVED = "observed"
    UNOBSERVED = "unobserved"


class ComparisonOutcome(StrEnum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"


class CheckpointProposalStatus(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class ContinuitySegmentRecord:
    segment_id: str
    subject_ref: SubjectRef
    segment_start_at: datetime
    segment_end_at: datetime
    status: ContinuitySegmentStatus
    as_of: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "segment_start_at",
            require_utc_datetime(
                self.segment_start_at, label="continuity segment segment_start_at"
            ),
        )
        object.__setattr__(
            self,
            "segment_end_at",
            require_utc_datetime(
                self.segment_end_at, label="continuity segment segment_end_at"
            ),
        )
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="continuity segment as_of"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "segment_id": self.segment_id,
            "subject_ref": _subject_ref_payload(self.subject_ref),
            "segment_start_at": format_temporal_value(
                self.segment_start_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="continuity segment segment_start_at",
            ),
            "segment_end_at": format_temporal_value(
                self.segment_end_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="continuity segment segment_end_at",
            ),
            "status": self.status.value,
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="continuity segment as_of",
            ),
        }


@dataclass(frozen=True)
class EventLinkRecord:
    event_link_id: str
    segment_id: str
    kind: str
    left_event_ref: str
    right_event_ref: str
    status: str

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "event_link_id": self.event_link_id,
            "segment_id": self.segment_id,
            "kind": self.kind,
            "left_event_ref": self.left_event_ref,
            "right_event_ref": self.right_event_ref,
            "status": self.status,
        }


@dataclass(frozen=True)
class BalanceTargetRecord:
    target_id: str
    segment_id: str
    subject_ref: SubjectRef
    kind: BalanceTargetKind
    as_of: datetime
    expected_value: AssertionValue
    observed_value: AssertionValue | None
    observation_status: BalanceTargetObservationStatus
    comparison_outcome: ComparisonOutcome | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="balance target as_of"),
        )
        if self.observation_status is BalanceTargetObservationStatus.OBSERVED:
            if self.observed_value is None:
                raise ValueError("observed balance targets require observed_value")
        elif self.comparison_outcome is not None:
            raise ValueError(
                "unobserved balance targets must not set comparison_outcome"
            )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "target_id": self.target_id,
            "segment_id": self.segment_id,
            "subject_ref": _subject_ref_payload(self.subject_ref),
            "kind": self.kind.value,
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="balance target as_of",
            ),
            "expected_value": assertion_value_payload(self.expected_value),
            "observed_value": (
                None
                if self.observed_value is None
                else assertion_value_payload(self.observed_value)
            ),
            "observation_status": self.observation_status.value,
            "comparison_outcome": (
                None
                if self.comparison_outcome is None
                else self.comparison_outcome.value
            ),
        }


@dataclass(frozen=True)
class CheckpointProposalRecord:
    proposal_id: str
    segment_id: str
    subject_ref: SubjectRef
    as_of: datetime
    status: CheckpointProposalStatus
    superseding_proposal_ref: str
    target_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "as_of",
            require_utc_datetime(self.as_of, label="checkpoint proposal as_of"),
        )

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "proposal_id": self.proposal_id,
            "segment_id": self.segment_id,
            "subject_ref": _subject_ref_payload(self.subject_ref),
            "as_of": format_temporal_value(
                self.as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint proposal as_of",
            ),
            "status": self.status.value,
            "superseding_proposal_ref": self.superseding_proposal_ref,
            "target_refs": list(sorted(self.target_refs)),
            "evidence_refs": list(sorted(self.evidence_refs)),
        }


@dataclass(frozen=True)
class ReconciliationState:
    reconciliation_state_id: str
    economic_facts_ref: str
    continuity_segment_records: tuple[ContinuitySegmentRecord, ...]
    event_link_records: tuple[EventLinkRecord, ...]
    balance_target_records: tuple[BalanceTargetRecord, ...]
    checkpoint_proposal_records: tuple[CheckpointProposalRecord, ...]

    def to_payload(self) -> dict[str, JsonValue]:
        return {
            "reconciliation_state_id": self.reconciliation_state_id,
            "schema_version": RECONCILIATION_STATE_SCHEMA_VERSION,
            "economic_facts_ref": self.economic_facts_ref,
            "continuity_segment_records": [
                item.to_payload()
                for item in canonical_continuity_segment_records(
                    self.continuity_segment_records
                )
            ],
            "event_link_records": [
                item.to_payload() for item in self.event_link_records
            ],
            "balance_target_records": [
                item.to_payload()
                for item in canonical_balance_target_records(
                    self.balance_target_records
                )
            ],
            "checkpoint_proposal_records": [
                item.to_payload()
                for item in canonical_checkpoint_proposal_records(
                    self.checkpoint_proposal_records
                )
            ],
        }


def stable_continuity_segment_id(
    *, subject_ref: SubjectRef, segment_start_at: datetime, segment_end_at: datetime
) -> str:
    return _stable_id(
        [
            _subject_ref_payload(subject_ref),
            format_temporal_value(
                segment_start_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="continuity segment segment_start_at",
            ),
            format_temporal_value(
                segment_end_at,
                precision=TemporalPrecision.TIMESTAMP,
                label="continuity segment segment_end_at",
            ),
        ]
    )


def stable_reconciliation_state_id(*, economic_facts_ref: str, segment_id: str) -> str:
    return _stable_product_id([economic_facts_ref, segment_id])


def stable_balance_target_id(
    *,
    segment_id: str,
    subject_ref: SubjectRef,
    kind: BalanceTargetKind,
    as_of: datetime,
    expected_value: AssertionValue,
) -> str:
    return _stable_id(
        [
            segment_id,
            _subject_ref_payload(subject_ref),
            kind.value,
            format_temporal_value(
                as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="balance target as_of",
            ),
            assertion_value_fingerprint(expected_value),
        ]
    )


def stable_checkpoint_proposal_id(
    *,
    segment_id: str,
    subject_ref: SubjectRef,
    as_of: datetime,
    target_refs: tuple[str, ...],
) -> str:
    return _stable_id(
        [
            segment_id,
            _subject_ref_payload(subject_ref),
            format_temporal_value(
                as_of,
                precision=TemporalPrecision.TIMESTAMP,
                label="checkpoint proposal as_of",
            ),
            list(sorted(target_refs)),
        ]
    )


def canonical_continuity_segment_records(
    records: tuple[ContinuitySegmentRecord, ...],
) -> tuple[ContinuitySegmentRecord, ...]:
    return tuple(sorted(records, key=lambda item: (item.as_of, item.segment_id)))


def canonical_balance_target_records(
    records: tuple[BalanceTargetRecord, ...],
) -> tuple[BalanceTargetRecord, ...]:
    return tuple(
        sorted(records, key=lambda item: (item.segment_id, item.as_of, item.target_id))
    )


def canonical_checkpoint_proposal_records(
    records: tuple[CheckpointProposalRecord, ...],
) -> tuple[CheckpointProposalRecord, ...]:
    return tuple(
        sorted(
            records, key=lambda item: (item.as_of, item.segment_id, item.proposal_id)
        )
    )


def reconciliation_state_fingerprint(state: ReconciliationState) -> str:
    return sha256(_json_text(state.to_payload()).encode("utf-8")).hexdigest()
