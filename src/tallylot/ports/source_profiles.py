"""Boundary contracts for source discovery and profiling."""

from __future__ import annotations

from dataclasses import dataclass, field

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue, SourceId


def _empty_metadata() -> dict[str, str]:
    return {}


def _empty_object_map() -> dict[str, JsonValue]:
    return {}


@dataclass(frozen=True)
class FileInventoryEntry:
    relative_path: str
    suffix: str
    size_bytes: int
    sha256: str
    source_path: str = ""
    bundle_id: str = ""
    bundle_type: str = ""
    bundle_relative_path: str = ""
    alias_group: str = ""
    collision_status: str = ""
    path_scope_tokens: str = ""
    content_scope_tokens: str = ""
    scope_tokens: str = ""
    scope_preview: str = ""
    archive_source_path: str = ""
    archive_member_path: str = ""
    row_count: int | None = None
    family: str = ""
    header_preview: str = ""
    header: tuple[str, ...] = ()
    date_field: str = ""
    min_timestamp: str = ""
    max_timestamp: str = ""
    timestamp_resolution: str = ""
    timezone_mode: str = ""
    timezone_value: str = ""
    timezone_conflict: str = ""
    export_timestamp: str = ""
    report_period_start: str = ""
    report_period_end: str = ""
    workbook_sheet_names: str = ""
    workbook_created_at: str = ""
    workbook_modified_at: str = ""
    artifact_kind: str = ""
    artifact_reason: str = ""


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
            "file_inventory": [item.__dict__ for item in self.file_inventory],
        }


@dataclass(frozen=True)
class VerificationExportSet:
    validate_transactions: str
    missing_transactions: str
    duplicate_transactions: str
    current_balance: str
    balance_by_exchange: str
