from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tallylot.application.profiling import BuildProfileUseCase, ProfileRequest
from tallylot.application.resource_refs import to_resource_ref
from tallylot.application.profiling.artifacts import write_profile_artifacts
from tallylot.domain.types import AdapterId, CaptureUid, SourceId
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.source_profiles import (
    PROFILE_INVENTORY_HEADER,
    FileInventoryEntry,
    SourceProfile,
)
from tallylot.ports.captures import (
    CAPTURE_METADATA_FIELDS,
    SOURCE_CAPTURE_HEADER,
    SOURCE_INVENTORY_HEADER,
    CaptureMetadata,
    SourceCaptureRecord,
    SourceInventorySummaryRecord,
)
from repo_support.capture_roots import materialize_capture_root
from tests.support.services import FakeSourceRegistry, MatchingSourceAdapter


def test_capture_metadata_uses_expected_json_fields() -> None:
    metadata = CaptureMetadata(
        capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
        source=SourceId("binance"),
        capture_label="2026-03-23T14-15-16Z",
        intake_started_at=datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC),
        intake_completed_at=datetime(2026, 3, 23, 14, 19, 4, tzinfo=UTC),
        intake_method="source_intake_apply",
        incoming_ref="incoming/binance",
        manifest_fingerprint="manifest:fixture",
        status="captured",
        notes="",
    )

    payload = metadata.to_dict()

    assert tuple(payload.keys()) == CAPTURE_METADATA_FIELDS
    assert CaptureMetadata.from_dict(payload) == metadata


def test_source_capture_record_uses_expected_header() -> None:
    row = SourceCaptureRecord(
        capture_uid=CaptureUid("01HV4A5H7VJH7M3Y5A6B7C8D9E"),
        source=SourceId("binance"),
        capture_label="2026-03-23T14-15-16Z",
        status="captured",
        intake_started_at=datetime(2026, 3, 23, 14, 15, 16, tzinfo=UTC),
        intake_completed_at=datetime(2026, 3, 23, 14, 19, 4, tzinfo=UTC),
        intake_method="source_intake_apply",
        incoming_ref="incoming/binance",
        capture_root_ref="evidence/raw/source/binance/2026-03-23T14-15-16Z",
        manifest_fingerprint="manifest:fixture",
        file_count=4,
        observed_period_start="2026-01-01",
        observed_period_end="2026-03-23",
        observed_group_count=2,
        notes="",
    ).to_row()

    assert tuple(row.keys()) == SOURCE_CAPTURE_HEADER


def test_source_inventory_summary_record_uses_expected_header() -> None:
    row = SourceInventorySummaryRecord(
        source=SourceId("binance"),
        activity_after_cutoff="yes",
        scope_status="in_scope",
        status="capture_complete",
        capture_count=2,
        latest_capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
        latest_capture_label="2026-03-23T14-15-16Z",
        latest_capture_completed_at=datetime(2026, 3, 23, 14, 19, 4, tzinfo=UTC),
        assembly_status="pending",
        assembled_root_ref="working/normalized/sources/binance",
        adapter_hints="binance",
        notes="",
    ).to_row()

    assert tuple(row.keys()) == SOURCE_INVENTORY_HEADER


def test_profile_inventory_writer_uses_expected_header(tmp_path: Path) -> None:
    profile = SourceProfile(
        source=SourceId("binance"),
        raw_dir=str(tmp_path / "raw"),
        adapter_id=AdapterId("binance"),
        manifest_fingerprint="manifest:fixture",
        file_inventory=(
            FileInventoryEntry(
                relative_path="statement.pdf",
                suffix=".pdf",
                size_bytes=1024,
                sha256="fixture",
                capture_uid="01HV4A5H7VJH7M3Y5A6B7C8D9E",
                source="binance",
                evidence_role="statement",
                observed_period_start="2026-01-01",
                observed_period_end="2026-03-23",
                observed_period_label="2026-Q1",
                statement_kind="balance_statement",
                originality_class="original",
            ),
        ),
        supported=True,
    )
    artifacts = FilesystemArtifactStore()
    output_dir = tmp_path / "profile"

    write_profile_artifacts(artifacts, profile, output_dir)

    rows = artifacts.read_rows(output_dir / "profile_inventory.csv")

    assert tuple(rows[0].keys()) == PROFILE_INVENTORY_HEADER


def test_profile_service_writes_capture_metadata_columns_from_capture_root(
    tmp_path: Path,
) -> None:
    raw_capture_root = materialize_capture_root(tmp_path, source="fixture_source")
    (raw_capture_root / "transactions.csv").write_text(
        "timestamp,amount\n2026-03-23 14:15:16,1\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "profile"
    artifacts = FilesystemArtifactStore()

    BuildProfileUseCase(
        FakeSourceRegistry(source_adapters=(MatchingSourceAdapter("fixture_source"),)),
        artifacts,
    ).execute(
        ProfileRequest(
            source="fixture_source",
            raw_capture_ref=to_resource_ref(raw_capture_root),
            profile_output_ref=to_resource_ref(output_dir),
        )
    )

    rows = artifacts.read_rows(output_dir / "profile_inventory.csv")

    assert rows[0]["capture_uid"] == "01HV4A5H7VJH7M3Y5A6B7C8D9E"
    assert rows[0]["source"] == "fixture_source"
