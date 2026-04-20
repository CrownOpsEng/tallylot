"""Filesystem ReconciliationState repository."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Sequence, cast

from tallylot.domain.assertion import (
    LocationValue,
    MoneyValue,
    OwnerValue,
    QuantityValue,
)
from tallylot.domain.reconciliation import (
    RECONCILIATION_STATE_SCHEMA_VERSION,
    BalanceTargetKind,
    BalanceTargetObservationStatus,
    BalanceTargetRecord,
    CheckpointProposalRecord,
    CheckpointProposalStatus,
    ComparisonOutcome,
    ContinuitySegmentRecord,
    ContinuitySegmentStatus,
    EventLinkRecord,
    ReconciliationState,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore


class FilesystemReconciliationStateRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def write_reconciliation_state(
        self, path: Path, reconciliation_state: ReconciliationState
    ) -> None:
        self._artifacts.write_json(path, reconciliation_state.to_payload())

    def read_reconciliation_state(self, path: Path) -> ReconciliationState:
        payload = _required_dict(
            json.loads(path.read_text(encoding="utf-8")), "payload"
        )
        schema_version = payload.get("schema_version")
        if schema_version != RECONCILIATION_STATE_SCHEMA_VERSION:
            rendered = "<missing>" if schema_version in (None, "") else schema_version
            raise ValueError(
                "unsupported reconciliation state schema_version: "
                f"{rendered}; expected {RECONCILIATION_STATE_SCHEMA_VERSION}"
            )
        return ReconciliationState(
            reconciliation_state_id=_required_text(payload, "reconciliation_state_id"),
            economic_facts_ref=_required_text(payload, "economic_facts_ref"),
            continuity_segment_records=tuple(
                _segment_from_payload(item)
                for item in _required_list(payload, "continuity_segment_records")
            ),
            event_link_records=tuple(
                _event_link_from_payload(item)
                for item in _required_list(payload, "event_link_records")
            ),
            balance_target_records=tuple(
                _target_from_payload(item)
                for item in _required_list(payload, "balance_target_records")
            ),
            checkpoint_proposal_records=tuple(
                _proposal_from_payload(item)
                for item in _required_list(payload, "checkpoint_proposal_records")
            ),
        )


def _segment_from_payload(payload: object) -> ContinuitySegmentRecord:
    raw = _required_dict(payload, "continuity segment")
    return ContinuitySegmentRecord(
        segment_id=_required_text(raw, "segment_id"),
        subject_ref=_required_subject_ref(raw, "subject_ref"),
        segment_start_at=_required_temporal(raw, "segment_start_at"),
        segment_end_at=_required_temporal(raw, "segment_end_at"),
        status=ContinuitySegmentStatus(_required_text(raw, "status")),
        as_of=_required_temporal(raw, "as_of"),
    )


def _event_link_from_payload(payload: object) -> EventLinkRecord:
    raw = _required_dict(payload, "event link")
    return EventLinkRecord(
        event_link_id=_required_text(raw, "event_link_id"),
        segment_id=_required_text(raw, "segment_id"),
        kind=_required_text(raw, "kind"),
        left_event_ref=_required_text(raw, "left_event_ref"),
        right_event_ref=_required_text(raw, "right_event_ref"),
        status=_required_text(raw, "status"),
    )


def _target_from_payload(payload: object) -> BalanceTargetRecord:
    raw = _required_dict(payload, "balance target")
    observed_value_payload = raw.get("observed_value")
    return BalanceTargetRecord(
        target_id=_required_text(raw, "target_id"),
        segment_id=_required_text(raw, "segment_id"),
        subject_ref=_required_subject_ref(raw, "subject_ref"),
        kind=BalanceTargetKind(_required_text(raw, "kind")),
        as_of=_required_temporal(raw, "as_of"),
        expected_value=_required_assertion_value(raw, "expected_value"),
        observed_value=(
            None
            if observed_value_payload is None
            else _assertion_value_from_payload(observed_value_payload)
        ),
        observation_status=BalanceTargetObservationStatus(
            _required_text(raw, "observation_status")
        ),
        comparison_outcome=(
            None
            if raw.get("comparison_outcome") in (None, "")
            else ComparisonOutcome(_required_text(raw, "comparison_outcome"))
        ),
    )


def _proposal_from_payload(payload: object) -> CheckpointProposalRecord:
    raw = _required_dict(payload, "checkpoint proposal")
    return CheckpointProposalRecord(
        proposal_id=_required_text(raw, "proposal_id"),
        segment_id=_required_text(raw, "segment_id"),
        subject_ref=_required_subject_ref(raw, "subject_ref"),
        as_of=_required_temporal(raw, "as_of"),
        status=CheckpointProposalStatus(_required_text(raw, "status")),
        superseding_proposal_ref=_optional_text(raw, "superseding_proposal_ref"),
        target_refs=_required_text_tuple(raw, "target_refs"),
        evidence_refs=_required_text_tuple(raw, "evidence_refs"),
    )


def _required_assertion_value(
    payload: dict[str, object], key: str
) -> QuantityValue | MoneyValue | OwnerValue | LocationValue:
    value = payload.get(key)
    return _assertion_value_from_payload(value)


def _assertion_value_from_payload(
    payload: object,
) -> QuantityValue | MoneyValue | OwnerValue | LocationValue:
    if not isinstance(payload, list):
        raise ValueError("invalid reconciliation assertion value: expected array")
    parts = cast(list[object], payload)
    if len(parts) != 2 or not isinstance(parts[0], str):
        raise ValueError(
            "invalid reconciliation assertion value: expected tagged array"
        )
    kind = parts[0]
    value_payload = parts[1]
    if kind == "quantity":
        items = _required_list_object(value_payload, "quantity assertion value")
        return QuantityValue(
            quantity=_required_decimal_text(
                _required_list_item(items, 0, "quantity amount")
            ),
            subject_ref=_subject_ref_from_payload(
                _required_list_item(items, 1, "quantity subject_ref")
            ),
        )
    if kind == "money":
        items = _required_list_object(value_payload, "money assertion value")
        currency = _required_list_item(items, 1, "money currency")
        if not isinstance(currency, str):
            raise ValueError("invalid reconciliation money value: expected currency")
        return MoneyValue(
            amount=_required_decimal_text(
                _required_list_item(items, 0, "money amount")
            ),
            currency=currency,
        )
    if kind == "owner":
        items = _required_list_object(value_payload, "owner assertion value")
        return OwnerValue(
            legal_owner_ref=_optional_list_text(items, 0),
            beneficial_owner_ref=_optional_list_text(items, 1),
            counterparty_ref=_optional_list_text(items, 2),
        )
    if kind == "location":
        items = _required_list_object(value_payload, "location assertion value")
        location_ref = _required_list_item(items, 0, "location ref")
        if not isinstance(location_ref, str):
            raise ValueError("invalid reconciliation location value")
        return LocationValue(location_ref=location_ref)
    raise ValueError(f"invalid reconciliation assertion value kind: {kind}")


def _optional_list_text(items: list[object], index: int) -> str:
    value = items[index] if index < len(items) else ""
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError("invalid reconciliation owner value")
    return value


def _required_list_item(items: list[object], index: int, label: str) -> object:
    if index >= len(items):
        raise ValueError(f"invalid reconciliation assertion value: missing {label}")
    return items[index]


def _required_list_object(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"invalid reconciliation {label}: expected array")
    return cast(list[object], value)


def _required_subject_ref(
    payload: dict[str, object], key: str
) -> tuple[str, tuple[object, ...]]:
    return _subject_ref_from_payload(payload.get(key))


def _subject_ref_from_payload(value: object) -> tuple[str, tuple[object, ...]]:
    if not isinstance(value, list):
        raise ValueError("invalid reconciliation subject_ref: expected array")
    parts = cast(list[object], value)
    if len(parts) != 2 or not isinstance(parts[0], str):
        raise ValueError("invalid reconciliation subject_ref: expected array")
    raw_key = parts[1]
    if not isinstance(raw_key, list):
        raise ValueError("invalid reconciliation subject_ref: expected key array")
    return (parts[0], _tupled(cast(list[object], raw_key)))


def _tupled(value: Sequence[object]) -> tuple[object, ...]:
    return tuple(_tupled_item(item) for item in value)


def _tupled_item(value: object) -> object:
    if isinstance(value, list):
        return _tupled(cast(list[object], value))
    return value


def _required_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"invalid reconciliation state {label}: expected object")
    raw = cast(dict[object, object], value)
    return {str(key): item for key, item in raw.items()}


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid reconciliation state {key}: expected array")
    return cast(list[object], value)


def _required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if not isinstance(value, str) or value == "":
        raise ValueError(
            f"invalid reconciliation state {key}: expected non-empty string"
        )
    return value


def _optional_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key, "")
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ValueError(f"invalid reconciliation state {key}: expected string")
    return value


def _required_text_tuple(payload: dict[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"invalid reconciliation state {key}: expected array")
    items = cast(list[object], value)
    if not all(isinstance(item, str) for item in items):
        raise ValueError(f"invalid reconciliation state {key}: expected string array")
    return tuple(cast(list[str], items))


def _required_temporal(payload: dict[str, object], key: str) -> datetime:
    return parse_temporal_value(
        _required_text(payload, key), precision=TemporalPrecision.TIMESTAMP
    )


def _required_decimal_text(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("invalid reconciliation decimal value")
    parsed = parse_decimal(value)
    if parsed is None:
        raise ValueError("invalid reconciliation decimal value")
    return parsed
