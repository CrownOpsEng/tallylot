from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from tallylot.domain.assertion import QuantityValue
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
    ReconciliationState,
)
from tallylot.domain.types import JsonValue
from tallylot.infrastructure.storage import FilesystemReconciliationStateRepository


def _sample_state() -> ReconciliationState:
    subject_ref = (
        "position",
        (
            ("beneficial_owner:filing",),
            ("location:coinbase",),
            ("instrument:btc",),
            None,
            "held_position",
        ),
    )
    as_of = datetime(2026, 3, 22, 23, 59, 59, tzinfo=UTC)
    expected = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    return ReconciliationState(
        reconciliation_state_id="state-1",
        economic_facts_ref="facts-1",
        continuity_segment_records=(
            ContinuitySegmentRecord(
                segment_id="segment-1",
                subject_ref=subject_ref,
                segment_start_at=datetime(2024, 2, 8, 16, 31, 22, tzinfo=UTC),
                segment_end_at=as_of,
                status=ContinuitySegmentStatus.COMPLETE,
                as_of=as_of,
            ),
        ),
        event_link_records=(),
        balance_target_records=(
            BalanceTargetRecord(
                target_id="target-1",
                segment_id="segment-1",
                subject_ref=subject_ref,
                kind=BalanceTargetKind.EXACT_BALANCE,
                as_of=as_of,
                expected_value=expected,
                observed_value=expected,
                observation_status=BalanceTargetObservationStatus.OBSERVED,
                comparison_outcome=ComparisonOutcome.MATCHED,
            ),
        ),
        checkpoint_proposal_records=(
            CheckpointProposalRecord(
                proposal_id="proposal-1",
                segment_id="segment-1",
                subject_ref=subject_ref,
                as_of=as_of,
                status=CheckpointProposalStatus.READY,
                superseding_proposal_ref="",
                target_refs=("target-1",),
                evidence_refs=("observation:document", "observation:row"),
            ),
        ),
    )


def test_reconciliation_state_repository_round_trips_json_payload(
    tmp_path: Path,
) -> None:
    repository = FilesystemReconciliationStateRepository()
    state = _sample_state()
    path = (
        tmp_path
        / "working"
        / "products"
        / "reconciliation_states"
        / "state-1"
        / "reconciliation_state.json"
    )

    repository.write_reconciliation_state(path, state)

    payload = json.loads(path.read_text(encoding="utf-8"))
    round_trip = repository.read_reconciliation_state(path)

    assert payload["schema_version"] == RECONCILIATION_STATE_SCHEMA_VERSION
    assert payload["event_link_records"] == []
    assert round_trip == state


def test_reconciliation_state_repository_rejects_missing_schema_version(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reconciliation_state.json"
    payload = _sample_state().to_payload()
    payload.pop("schema_version")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported reconciliation state schema_version: <missing>; expected "
            f"{RECONCILIATION_STATE_SCHEMA_VERSION}"
        ),
    ):
        FilesystemReconciliationStateRepository().read_reconciliation_state(path)


def test_reconciliation_state_repository_rejects_wrong_schema_version(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reconciliation_state.json"
    payload = _sample_state().to_payload()
    payload["schema_version"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported reconciliation state schema_version: 99; expected "
            f"{RECONCILIATION_STATE_SCHEMA_VERSION}"
        ),
    ):
        FilesystemReconciliationStateRepository().read_reconciliation_state(path)


def test_reconciliation_state_repository_rejects_truncated_quantity_value(
    tmp_path: Path,
) -> None:
    path = tmp_path / "reconciliation_state.json"
    payload = _sample_state().to_payload()
    balance_target_records = cast(list[JsonValue], payload["balance_target_records"])
    first_target = cast(dict[str, JsonValue], balance_target_records[0])
    first_target["expected_value"] = cast(JsonValue, ["quantity", ["1.25"]])
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="invalid reconciliation assertion value: missing quantity subject_ref",
    ):
        FilesystemReconciliationStateRepository().read_reconciliation_state(path)
