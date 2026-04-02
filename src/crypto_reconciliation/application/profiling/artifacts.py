"""Profile artifact writers."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.source_profiles import SourceProfile

ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "context_timestamp",
    "raw_file",
    "raw_row_ref",
    "status",
)


def write_profile_artifacts(
    artifacts: ArtifactStorePort,
    profile: SourceProfile,
    output_dir: Path,
) -> None:
    artifacts.write_json(output_dir / "profile.json", cast(JsonValue, profile.to_dict()))
    artifacts.write_rows(
        output_dir / "profile_inventory.csv",
        (
            "source_path",
            "relative_path",
            "bundle_id",
            "bundle_type",
            "bundle_relative_path",
            "alias_group",
            "collision_status",
            "path_scope_tokens",
            "content_scope_tokens",
            "scope_tokens",
            "scope_preview",
            "suffix",
            "family",
            "header_preview",
            "size_bytes",
            "sha256",
            "archive_source_path",
            "archive_member_path",
            "row_count",
            "header",
            "date_field",
            "min_timestamp",
            "max_timestamp",
            "timestamp_resolution",
            "timezone_mode",
            "timezone_value",
            "timezone_conflict",
            "export_timestamp",
            "report_period_start",
            "report_period_end",
            "workbook_sheet_names",
            "workbook_created_at",
            "workbook_modified_at",
            "artifact_kind",
            "artifact_reason",
        ),
        (
            {
                "source_path": entry.source_path or entry.relative_path,
                "relative_path": entry.relative_path,
                "bundle_id": entry.bundle_id,
                "bundle_type": entry.bundle_type,
                "bundle_relative_path": entry.bundle_relative_path,
                "alias_group": entry.alias_group,
                "collision_status": entry.collision_status,
                "path_scope_tokens": entry.path_scope_tokens,
                "content_scope_tokens": entry.content_scope_tokens,
                "scope_tokens": entry.scope_tokens,
                "scope_preview": entry.scope_preview,
                "suffix": entry.suffix,
                "family": entry.family,
                "header_preview": entry.header_preview,
                "size_bytes": str(entry.size_bytes),
                "sha256": entry.sha256,
                "archive_source_path": entry.archive_source_path,
                "archive_member_path": entry.archive_member_path,
                "row_count": "" if entry.row_count is None else str(entry.row_count),
                "header": "|".join(entry.header),
                "date_field": entry.date_field,
                "min_timestamp": entry.min_timestamp,
                "max_timestamp": entry.max_timestamp,
                "timestamp_resolution": entry.timestamp_resolution,
                "timezone_mode": entry.timezone_mode,
                "timezone_value": entry.timezone_value,
                "timezone_conflict": entry.timezone_conflict,
                "export_timestamp": entry.export_timestamp,
                "report_period_start": entry.report_period_start,
                "report_period_end": entry.report_period_end,
                "workbook_sheet_names": entry.workbook_sheet_names,
                "workbook_created_at": entry.workbook_created_at,
                "workbook_modified_at": entry.workbook_modified_at,
                "artifact_kind": entry.artifact_kind,
                "artifact_reason": entry.artifact_reason,
            }
            for entry in profile.file_inventory
        ),
    )
    artifacts.write_rows(
        output_dir / "profile_issues.csv",
        ISSUE_HEADER,
        (issue.to_row() for issue in profile.scan_issues),
    )
    artifacts.write_rows(
        output_dir / "timezone_issues.csv",
        ISSUE_HEADER,
        (issue.to_row() for issue in profile.timezone_issues),
    )
