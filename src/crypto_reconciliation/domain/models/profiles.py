"""Source-profile domain models."""

from __future__ import annotations

from dataclasses import dataclass, field

from crypto_reconciliation.domain.types import AdapterId, JsonValue, SourceId

from .inventory import FileInventoryEntry
from .issues import IssueRecord


def _empty_metadata() -> dict[str, str]:
    return {}


def _empty_object_map() -> dict[str, JsonValue]:
    return {}


@dataclass(frozen=True)
class SourceProfile:
    source: SourceId
    raw_dir: str
    adapter_id: AdapterId
    manifest_fingerprint: str
    file_inventory: tuple[FileInventoryEntry, ...]
    supported: bool
    metadata: dict[str, str] = field(default_factory=_empty_metadata)
    normalization_hints: dict[str, JsonValue] = field(default_factory=_empty_object_map)
    timezone_summary: dict[str, JsonValue] = field(default_factory=_empty_object_map)
    scan_issues: tuple[IssueRecord, ...] = ()
    timezone_issues: tuple[IssueRecord, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "source": str(self.source),
            "raw_dir": self.raw_dir,
            "adapter_id": str(self.adapter_id),
            "manifest_fingerprint": self.manifest_fingerprint,
            "supported": self.supported,
            "metadata": dict(self.metadata),
            "normalization_hints": dict(self.normalization_hints),
            "timezone_summary": dict(self.timezone_summary),
            "scan_issues": [issue.to_row() for issue in self.scan_issues],
            "file_inventory": [
                {
                    "relative_path": item.relative_path,
                    "suffix": item.suffix,
                    "size_bytes": item.size_bytes,
                    "sha256": item.sha256,
                    "source_path": item.source_path,
                    "bundle_id": item.bundle_id,
                    "bundle_type": item.bundle_type,
                    "bundle_relative_path": item.bundle_relative_path,
                    "alias_group": item.alias_group,
                    "collision_status": item.collision_status,
                    "path_scope_tokens": item.path_scope_tokens,
                    "content_scope_tokens": item.content_scope_tokens,
                    "scope_tokens": item.scope_tokens,
                    "scope_preview": item.scope_preview,
                    "archive_source_path": item.archive_source_path,
                    "archive_member_path": item.archive_member_path,
                    "row_count": item.row_count,
                    "family": item.family,
                    "header_preview": item.header_preview,
                    "header": list(item.header),
                    "date_field": item.date_field,
                    "min_timestamp": item.min_timestamp,
                    "max_timestamp": item.max_timestamp,
                    "timestamp_resolution": item.timestamp_resolution,
                    "timezone_mode": item.timezone_mode,
                    "timezone_value": item.timezone_value,
                    "timezone_conflict": item.timezone_conflict,
                    "export_timestamp": item.export_timestamp,
                    "report_period_start": item.report_period_start,
                    "report_period_end": item.report_period_end,
                    "workbook_sheet_names": item.workbook_sheet_names,
                    "workbook_created_at": item.workbook_created_at,
                    "workbook_modified_at": item.workbook_modified_at,
                    "artifact_kind": item.artifact_kind,
                    "artifact_reason": item.artifact_reason,
                }
                for item in self.file_inventory
            ],
        }


@dataclass(frozen=True)
class VerificationExportSet:
    validate_transactions: str
    missing_transactions: str
    duplicate_transactions: str
    current_balance: str
    balance_by_exchange: str
