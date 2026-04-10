from __future__ import annotations

from datetime import UTC, datetime

from tallylot.domain.types import CaptureUid, SourceId
from tallylot.ports.captures import (
    CAPTURE_METADATA_FIELDS,
    SOURCE_CAPTURE_HEADER,
    SOURCE_INVENTORY_HEADER,
    CaptureMetadata,
    SourceCaptureRecord,
    SourceInventorySummaryRecord,
)


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
