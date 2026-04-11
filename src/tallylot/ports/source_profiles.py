"""Boundary contracts for source discovery and profiling."""

from __future__ import annotations

from dataclasses import dataclass, field

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import AdapterId, JsonValue, SourceId


def _empty_metadata() -> dict[str, str]:
    return {}


def _empty_object_map() -> dict[str, JsonValue]:
    return {}


PROFILE_INVENTORY_HEADER = (
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
    "capture_uid",
    "source",
    "evidence_role",
    "observed_period_start",
    "observed_period_end",
    "observed_period_label",
    "statement_kind",
    "originality_class",
)


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
    capture_uid: str = ""
    source: str = ""
    evidence_role: str = ""
    observed_period_start: str = ""
    observed_period_end: str = ""
    observed_period_label: str = ""
    statement_kind: str = ""
    originality_class: str = ""


@dataclass(frozen=True)
class FileFamilyClaim:
    relative_path: str
    adapter_id: AdapterId
    family_id: str
    confidence: str = "high"

    @property
    def token(self) -> str:
        return family_claim_token(str(self.adapter_id), self.family_id)


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


def family_claim_token(adapter_id: str, family_id: str) -> str:
    return f"{adapter_id}:{family_id}"


def parse_family_claim_tokens(value: str) -> tuple[tuple[str, str], ...]:
    claims: list[tuple[str, str]] = []
    for token in (item.strip() for item in value.split(";")):
        if not token or ":" not in token:
            continue
        adapter_id, family_id = token.split(":", 1)
        if not adapter_id or not family_id:
            continue
        claims.append((adapter_id, family_id))
    return tuple(claims)
