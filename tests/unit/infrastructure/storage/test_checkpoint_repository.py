from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from tallylot.domain.assertion import QuantityValue
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
from tallylot.infrastructure.storage import FilesystemCheckpointRepository


def _sample_checkpoint() -> Checkpoint:
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
    accepted_value = QuantityValue(quantity=Decimal("1.25"), subject_ref=subject_ref)
    return Checkpoint(
        checkpoint_id="checkpoint-1",
        reconciliation_state_refs=("state-1",),
        as_of=as_of,
        checkpoint_records=(
            CheckpointRecord(
                checkpoint_id="checkpoint-1",
                as_of=as_of,
                assertion_ids=("assertion-1",),
                proposal_refs=("proposal-1",),
            ),
        ),
        checkpoint_assertion_records=(
            CheckpointAssertionRecord(
                assertion_id="assertion-1",
                checkpoint_id="checkpoint-1",
                subject_ref=subject_ref,
                kind=CheckpointAssertionValueKind.POSITION_QUANTITY,
                as_of=as_of,
                accepted_value=accepted_value,
                trust_level=CheckpointAssertionTrustLevel.FILING_READY,
                basis=CheckpointAssertionBasis.DOCUMENT_SUPPORT,
                support_shape=CheckpointAssertionSupportShape.DOCUMENT_OBSERVATION,
                continuity_kind=CheckpointAssertionContinuityKind.RECONCILED_ROLLFORWARD,
            ),
        ),
    )


def test_checkpoint_repository_round_trips_json_payload(tmp_path: Path) -> None:
    repository = FilesystemCheckpointRepository()
    checkpoint = _sample_checkpoint()
    path = (
        tmp_path
        / "working"
        / "products"
        / "checkpoints"
        / "checkpoint-1"
        / "checkpoint.json"
    )

    repository.write_checkpoint(path, checkpoint)

    payload = json.loads(path.read_text(encoding="utf-8"))
    round_trip = repository.read_checkpoint(path)

    assert payload["schema_version"] == CHECKPOINT_SCHEMA_VERSION
    assert round_trip == checkpoint


def test_checkpoint_repository_rejects_missing_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    payload = _sample_checkpoint().to_payload()
    payload.pop("schema_version")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported checkpoint schema_version: <missing>; expected "
            f"{CHECKPOINT_SCHEMA_VERSION}"
        ),
    ):
        FilesystemCheckpointRepository().read_checkpoint(path)


def test_checkpoint_repository_rejects_wrong_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    payload = _sample_checkpoint().to_payload()
    payload["schema_version"] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported checkpoint schema_version: 99; expected "
            f"{CHECKPOINT_SCHEMA_VERSION}"
        ),
    ):
        FilesystemCheckpointRepository().read_checkpoint(path)
