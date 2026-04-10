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
    SourceInventorySummaryRecord,
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
    workspace_root: Path,
    metadata: CaptureMetadata | None,
    plan: CaptureSessionPlan,
    capture_root_ref: str,
) -> None:
    path = workspace_root / "analysis" / "inventory" / "source_captures.csv"
    existing = artifacts.read_rows(path) if path.exists() else []
    existing.append(
        SourceCaptureRecord(
            capture_uid=metadata.capture_uid
            if metadata is not None
            else generate_capture_uid(now=datetime.now(UTC)),
            source=SourceId(plan.source_folder),
            capture_label=plan.capture_label,
            status=plan.capture_status if metadata is None else metadata.status,
            intake_started_at=metadata.intake_started_at
            if metadata is not None
            else None,
            intake_completed_at=metadata.intake_completed_at
            if metadata is not None
            else None,
            intake_method=metadata.intake_method
            if metadata is not None
            else "source_intake_apply",
            incoming_ref=metadata.incoming_ref if metadata is not None else "",
            capture_root_ref=capture_root_ref,
            manifest_fingerprint=plan.manifest_fingerprint,
            observed_period_start=plan.observed_period_start,
            observed_period_end=plan.observed_period_end,
            observed_group_count=plan.observed_group_count,
            supersedes_capture_uid="",
            notes="",
        ).to_row()
    )
    artifacts.write_rows(path, SOURCE_CAPTURE_HEADER, existing)


def update_source_inventory_summary(
    *,
    artifacts: ArtifactStorePort,
    workspace_root: Path,
    source: str,
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
    matching = [row for row in capture_rows if row.get("source", "") == source]
    latest = matching[-1] if matching else {}
    updated_row = SourceInventorySummaryRecord(
        source=SourceId(source),
        activity_after_cutoff=_existing_value(
            source_rows, source, "activity_after_cutoff"
        ),
        scope_status=_existing_value(source_rows, source, "scope_status") or "in_scope",
        status=_existing_value(source_rows, source, "status") or "capture_complete",
        capture_count=len(matching),
        latest_capture_uid=latest.get("capture_uid", ""),
        latest_capture_label=latest.get("capture_label", ""),
        latest_capture_completed_at=_parse_optional_timestamp(
            latest.get("intake_completed_at", "")
        ),
        assembly_status=_existing_value(source_rows, source, "assembly_status")
        or "pending",
        assembled_root_ref=_existing_value(source_rows, source, "assembled_root_ref"),
        adapter_hints=_existing_value(source_rows, source, "adapter_hints"),
        notes=_existing_value(source_rows, source, "notes"),
    ).to_row()
    remaining = [row for row in source_rows if row.get("source", "") != source]
    remaining.append(updated_row)
    artifacts.write_rows(source_inventory_path, tuple(updated_row.keys()), remaining)


def _existing_value(rows: list[dict[str, str]], source: str, field: str) -> str:
    for row in rows:
        if row.get("source", "") == source:
            return row.get(field, "")
    return ""


def _parse_optional_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
