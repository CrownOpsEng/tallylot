"""Capture persistence helpers for intake apply."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from tallylot.domain.captures import generate_capture_uid
from tallylot.domain.types import JsonValue, SourceId
from tallylot.ports.artifacts import ArtifactStorePort
from tallylot.ports.captures import (
    SOURCE_CAPTURE_HEADER,
    CaptureMetadata,
    SourceCaptureRecord,
)

from .lifecycle import (
    SourceInventorySummaryReduction,
    reduce_capture_status,
    reduce_source_inventory_summary,
)
from .session import CaptureSessionPlan


@dataclass(frozen=True)
class CaptureMetadataWrite:
    capture_root: Path
    source: str
    capture_label: str
    intake_started_at: datetime
    intake_completed_at: datetime
    incoming_ref: str
    manifest_fingerprint: str
    status: str


@dataclass(frozen=True)
class CaptureRecordWrite:
    workspace_root: Path
    metadata: CaptureMetadata | None
    plan: CaptureSessionPlan
    capture_root_ref: str
    intake_started_at: datetime
    intake_completed_at: datetime
    incoming_ref: str


def write_capture_metadata(
    *,
    artifacts: ArtifactStorePort,
    write: CaptureMetadataWrite,
) -> CaptureMetadata:
    metadata = CaptureMetadata(
        capture_uid=generate_capture_uid(now=write.intake_completed_at),
        source=SourceId(write.source),
        capture_label=write.capture_label,
        intake_started_at=write.intake_started_at,
        intake_completed_at=write.intake_completed_at,
        intake_method="source_intake_apply",
        incoming_ref=write.incoming_ref,
        manifest_fingerprint=write.manifest_fingerprint,
        status=write.status,
    )
    artifacts.write_json(
        write.capture_root / "capture.json", cast(JsonValue, metadata.to_dict())
    )
    return metadata


def append_capture_record(
    *,
    artifacts: ArtifactStorePort,
    write: CaptureRecordWrite,
) -> None:
    path = write.workspace_root / "analysis" / "inventory" / "source_captures.csv"
    existing = artifacts.read_rows(path) if path.exists() else []
    existing.append(
        SourceCaptureRecord(
            capture_uid=write.metadata.capture_uid
            if write.metadata is not None
            else generate_capture_uid(now=datetime.now(UTC)),
            source=SourceId(write.plan.source_folder),
            capture_label=write.plan.capture_label,
            status=(
                write.plan.capture_status
                if write.metadata is None
                else write.metadata.status
            ),
            intake_started_at=write.metadata.intake_started_at
            if write.metadata is not None
            else write.intake_started_at,
            intake_completed_at=write.metadata.intake_completed_at
            if write.metadata is not None
            else write.intake_completed_at,
            intake_method=write.metadata.intake_method
            if write.metadata is not None
            else "source_intake_apply",
            incoming_ref=write.metadata.incoming_ref
            if write.metadata is not None
            else write.incoming_ref,
            capture_root_ref=write.capture_root_ref,
            manifest_fingerprint=write.plan.manifest_fingerprint,
            file_count=write.plan.file_count,
            observed_period_start=write.plan.observed_period_start,
            observed_period_end=write.plan.observed_period_end,
            observed_group_count=write.plan.observed_group_count,
            supersedes_capture_uid="",
            notes="",
        ).to_row()
    )
    artifacts.write_rows(path, SOURCE_CAPTURE_HEADER, existing)


def append_capture_status_record(
    *,
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    capture_uid: str,
    status: str,
    notes: str = "",
) -> None:
    path = workspace_root / "analysis" / "inventory" / "source_captures.csv"
    rows = artifacts.read_rows(path) if path.exists() else []
    latest = _latest_capture_row(rows, capture_uid)
    if latest is None:
        return
    updated = {
        **latest,
        "status": reduce_capture_status(latest.get("status", ""), status),
    }
    if notes:
        updated["notes"] = notes
    rows.append(updated)
    artifacts.write_rows(path, SOURCE_CAPTURE_HEADER, rows)


def update_source_inventory_summary(  # pylint: disable=too-many-arguments
    *,
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    source: str,
    status: str | None = None,
    assembled_root_ref: str | None = None,
    assembled_output_present: bool | None = None,
    assembly_excluded_capture_count: int | None = None,
) -> None:
    source_inventory_path = (
        workspace_root / "analysis" / "issues" / "source_inventory.csv"
    )
    source_capture_path = (
        workspace_root / "analysis" / "inventory" / "source_captures.csv"
    )
    capture_rows = (
        artifacts.read_rows(source_capture_path) if source_capture_path.exists() else []
    )
    source_rows = (
        artifacts.read_rows(source_inventory_path)
        if source_inventory_path.exists()
        else []
    )
    updated_row = reduce_source_inventory_summary(
        reduction=SourceInventorySummaryReduction(
            source=source,
            capture_rows=capture_rows,
            source_rows=source_rows,
            requested_status=status,
            assembled_root_ref=assembled_root_ref,
            assembled_output_present=assembled_output_present,
            assembly_excluded_capture_count=assembly_excluded_capture_count,
        )
    )
    remaining = [row for row in source_rows if row.get("source", "") != source]
    remaining.append(updated_row)
    artifacts.write_rows(source_inventory_path, tuple(updated_row.keys()), remaining)


def _latest_capture_row(
    rows: list[dict[str, str]], capture_uid: str
) -> dict[str, str] | None:
    for row in reversed(rows):
        if row.get("capture_uid", "") == capture_uid:
            return row
    return None
