"""Inventory-oriented domain records."""

from __future__ import annotations

from dataclasses import dataclass


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
class WalletInventoryRecord:
    source: str
    identifier_kind: str
    identifier_value: str
    wallet_id: str = ""
    account: str = ""
    wallet: str = ""
    capture_path: str = ""
    normalized_identifier: str = ""
    display_identifier: str = ""
    network_scope: str = ""
    controller: str = ""
    account_label: str = ""
    evidence_kind: str = ""
    evidence_path: str = ""
    confidence: str = ""
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "capture_path": self.capture_path,
            "wallet_id": self.wallet_id,
            "identifier_kind": self.identifier_kind,
            "normalized_identifier": self.normalized_identifier or self.identifier_value,
            "display_identifier": self.display_identifier or self.identifier_value,
            "network_scope": self.network_scope,
            "controller": self.controller,
            "account_label": self.account_label,
            "evidence_kind": self.evidence_kind,
            "evidence_path": self.evidence_path,
            "confidence": self.confidence,
            "account": self.account,
            "wallet": self.wallet,
            "identifier_value": self.identifier_value,
            "notes": self.notes,
        }
