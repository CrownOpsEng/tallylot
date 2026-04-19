from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

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
from tallylot.domain.temporal import TemporalPrecision
from tallylot.infrastructure.storage import FilesystemEvidenceSetRepository


def _sample_evidence_set() -> EvidenceSet:
    return EvidenceSet(
        evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
        selection_fingerprint="fingerprint",
        capture_manifest_fingerprint="manifest-1",
        evidence_selection_records=(
            EvidenceSelectionRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                key=("retail_activity_export_file",),
                fingerprint="selection-fingerprint",
                basis=EvidenceSelectionBasis.SINGLE_MEMBER,
            ),
        ),
        evidence_member_records=(
            EvidenceMemberRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                selection_id="selection-1",
                member_id="member-1",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
                locator=("activity.csv", ""),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        evidence_observation_records=(
            EvidenceObservationRecord(
                evidence_set_id="coinbase:coinbase:capture-1:fingerprint",
                member_id="member-1",
                observation_id="observation-1",
                kind=EvidenceObservationKind.STATEMENT_BALANCE_ROW,
                key=("activity.csv", "", "row:0"),
                observed_at=datetime(2026, 3, 23, tzinfo=UTC),
                precision=TemporalPrecision.TIMESTAMP,
                quantity=Decimal("1.25"),
                instrument_symbol="BTC",
                balance_kind="asset_balance",
            ),
        ),
    )


def test_evidence_set_repository_round_trips_json_payload(tmp_path: Path) -> None:
    repository = FilesystemEvidenceSetRepository()
    evidence_set = _sample_evidence_set()
    path = (
        tmp_path
        / "working"
        / "products"
        / "evidence_sets"
        / "set-1"
        / "evidence_set.json"
    )

    repository.write_evidence_set(path, evidence_set)

    payload = json.loads(path.read_text(encoding="utf-8"))
    round_trip = repository.read_evidence_set(path)

    assert payload["schema_version"] == EVIDENCE_SET_SCHEMA_VERSION
    assert round_trip == evidence_set


def test_evidence_set_repository_rejects_missing_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "evidence_set.json"
    payload = _sample_evidence_set().to_payload()
    payload.pop("schema_version")
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "unsupported evidence set schema_version: <missing>; expected "
            f"{EVIDENCE_SET_SCHEMA_VERSION}"
        ),
    ):
        FilesystemEvidenceSetRepository().read_evidence_set(path)
