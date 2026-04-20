from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.evidence import (
    EvidenceMemberKind,
    EvidenceMemberRecord,
    EvidenceMemberStatus,
    EvidenceObservationKind,
    EvidenceObservationRecord,
    EvidenceSelectionBasis,
    EvidenceSelectionRecord,
)
from tallylot.domain.evidence.models import (
    selection_fingerprint_for_records,
    selection_record_fingerprints,
    stable_evidence_set_id,
    stable_member_id,
    stable_observation_id,
    stable_selection_id,
)
from tallylot.domain.temporal import TemporalPrecision


def test_stable_id_helpers_use_declared_recipes() -> None:
    evidence_set_id = stable_evidence_set_id(
        source_slug="coinbase",
        adapter_id="coinbase",
        capture_uid="capture-1",
        selection_fingerprint="fingerprint",
    )

    assert evidence_set_id == "coinbase:coinbase:capture-1:fingerprint"
    assert (
        stable_selection_id(
            evidence_set_id=evidence_set_id,
            key=("retail_activity_export_file",),
        )
        == "coinbase:coinbase:capture-1:fingerprint:retail_activity_export_file"
    )
    assert (
        stable_member_id(
            evidence_set_id=evidence_set_id,
            kind=EvidenceMemberKind.RETAIL_ACTIVITY_EXPORT_FILE,
            locator=("activity.csv", ""),
        )
        == "coinbase:coinbase:capture-1:fingerprint:retail_activity_export_file:activity.csv:"
    )
    assert (
        stable_observation_id(
            member_id="member-id",
            kind=EvidenceObservationKind.STATEMENT_DOCUMENT,
            key=("document",),
        )
        == "member-id:statement_document:document"
    )


def test_selection_fingerprints_ignore_ids_and_preserve_semantics() -> None:
    selection = EvidenceSelectionRecord(
        evidence_set_id="set-a",
        selection_id="selection-a",
        key=("statement_document", "statement.pdf", ""),
        fingerprint="",
        basis=EvidenceSelectionBasis.SINGLE_MEMBER,
        blocking_gap_refs=(),
    )
    member = EvidenceMemberRecord(
        evidence_set_id="set-a",
        selection_id="selection-a",
        member_id="member-a",
        source_slug="coinbase",
        adapter_id="coinbase",
        capture_uid="capture-1",
        kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
        locator=("statement.pdf", ""),
        status=EvidenceMemberStatus.SELECTED,
        capture_manifest_fingerprint="manifest-1",
    )
    observation = EvidenceObservationRecord(
        evidence_set_id="set-a",
        member_id="member-a",
        observation_id="observation-a",
        kind=EvidenceObservationKind.STATEMENT_BALANCE_ROW,
        key=("statement.pdf", "", "row:0"),
        observed_at=datetime(2026, 3, 23, tzinfo=UTC),
        precision=TemporalPrecision.TIMESTAMP,
        quantity=Decimal("1.5000"),
        instrument_symbol="BTC",
        balance_kind="asset_balance",
    )

    first = selection_fingerprint_for_records(
        selections=(selection,),
        members=(member,),
        observations=(observation,),
    )
    second = selection_fingerprint_for_records(
        selections=(selection,),
        members=(
            EvidenceMemberRecord(
                evidence_set_id="set-b",
                selection_id="selection-a",
                member_id="member-b",
                source_slug="coinbase",
                adapter_id="coinbase",
                capture_uid="capture-1",
                kind=EvidenceMemberKind.STATEMENT_DOCUMENT_FILE,
                locator=("statement.pdf", ""),
                status=EvidenceMemberStatus.SELECTED,
                capture_manifest_fingerprint="manifest-1",
            ),
        ),
        observations=(
            EvidenceObservationRecord(
                evidence_set_id="set-b",
                member_id="member-b",
                observation_id="observation-b",
                kind=EvidenceObservationKind.STATEMENT_BALANCE_ROW,
                key=("statement.pdf", "", "row:0"),
                observed_at=datetime(2026, 3, 23, tzinfo=UTC),
                precision=TemporalPrecision.TIMESTAMP,
                quantity=Decimal("1.5"),
                instrument_symbol="BTC",
                balance_kind="asset_balance",
            ),
        ),
    )

    assert first == second
    assert selection_record_fingerprints(
        selections=(selection,),
        members=(member,),
        observations=(observation,),
    )["selection-a"]
