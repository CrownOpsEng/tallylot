"""Capture metadata and registry artifact contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from tallylot.domain.types import CaptureUid, SourceId
from tallylot.domain.value_objects import format_timestamp, parse_timestamp

CAPTURE_METADATA_FIELDS = (
    "capture_uid",
    "source",
    "capture_label",
    "intake_started_at",
    "intake_completed_at",
    "intake_method",
    "incoming_ref",
    "manifest_fingerprint",
    "status",
    "notes",
)

SOURCE_CAPTURE_HEADER = (
    "capture_uid",
    "source",
    "capture_label",
    "status",
    "intake_started_at",
    "intake_completed_at",
    "intake_method",
    "incoming_ref",
    "capture_root_ref",
    "manifest_fingerprint",
    "file_count",
    "observed_period_start",
    "observed_period_end",
    "observed_group_count",
    "supersedes_capture_uid",
    "notes",
)

SOURCE_INVENTORY_HEADER = (
    "source",
    "activity_after_cutoff",
    "scope_status",
    "status",
    "capture_count",
    "latest_capture_uid",
    "latest_capture_label",
    "latest_capture_completed_at",
    "assembly_status",
    "assembled_root_ref",
    "adapter_hints",
    "notes",
)


def _optional_timestamp(value: datetime | None) -> str:
    return "" if value is None else format_timestamp(value)


def _optional_int(value: int | None) -> str:
    return "" if value is None else str(value)


@dataclass(frozen=True)
class CaptureMetadata:
    capture_uid: CaptureUid
    source: SourceId
    capture_label: str
    intake_started_at: datetime
    intake_completed_at: datetime
    intake_method: str
    incoming_ref: str
    manifest_fingerprint: str
    status: str
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "capture_uid": str(self.capture_uid),
            "source": str(self.source),
            "capture_label": self.capture_label,
            "intake_started_at": format_timestamp(self.intake_started_at),
            "intake_completed_at": format_timestamp(self.intake_completed_at),
            "intake_method": self.intake_method,
            "incoming_ref": self.incoming_ref,
            "manifest_fingerprint": self.manifest_fingerprint,
            "status": self.status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> CaptureMetadata:
        def required_text(key: str) -> str:
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"capture metadata field {key!r} must be a non-empty string"
                )
            return value

        return cls(
            capture_uid=CaptureUid(required_text("capture_uid")),
            source=SourceId(required_text("source")),
            capture_label=required_text("capture_label"),
            intake_started_at=parse_timestamp(required_text("intake_started_at")),
            intake_completed_at=parse_timestamp(required_text("intake_completed_at")),
            intake_method=required_text("intake_method"),
            incoming_ref=required_text("incoming_ref"),
            manifest_fingerprint=required_text("manifest_fingerprint"),
            status=required_text("status"),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True)
class SourceCaptureRecord:
    capture_uid: CaptureUid
    source: SourceId
    capture_label: str
    status: str
    intake_started_at: datetime | None = None
    intake_completed_at: datetime | None = None
    intake_method: str = ""
    incoming_ref: str = ""
    capture_root_ref: str = ""
    manifest_fingerprint: str = ""
    file_count: int | None = None
    observed_period_start: str = ""
    observed_period_end: str = ""
    observed_group_count: int | None = None
    supersedes_capture_uid: str = ""
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "capture_uid": str(self.capture_uid),
            "source": str(self.source),
            "capture_label": self.capture_label,
            "status": self.status,
            "intake_started_at": _optional_timestamp(self.intake_started_at),
            "intake_completed_at": _optional_timestamp(self.intake_completed_at),
            "intake_method": self.intake_method,
            "incoming_ref": self.incoming_ref,
            "capture_root_ref": self.capture_root_ref,
            "manifest_fingerprint": self.manifest_fingerprint,
            "file_count": _optional_int(self.file_count),
            "observed_period_start": self.observed_period_start,
            "observed_period_end": self.observed_period_end,
            "observed_group_count": _optional_int(self.observed_group_count),
            "supersedes_capture_uid": self.supersedes_capture_uid,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SourceInventorySummaryRecord:
    source: SourceId
    activity_after_cutoff: str = ""
    scope_status: str = ""
    status: str = ""
    capture_count: int | None = None
    latest_capture_uid: str = ""
    latest_capture_label: str = ""
    latest_capture_completed_at: datetime | None = None
    assembly_status: str = ""
    assembled_root_ref: str = ""
    adapter_hints: str = ""
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": str(self.source),
            "activity_after_cutoff": self.activity_after_cutoff,
            "scope_status": self.scope_status,
            "status": self.status,
            "capture_count": _optional_int(self.capture_count),
            "latest_capture_uid": self.latest_capture_uid,
            "latest_capture_label": self.latest_capture_label,
            "latest_capture_completed_at": _optional_timestamp(
                self.latest_capture_completed_at
            ),
            "assembly_status": self.assembly_status,
            "assembled_root_ref": self.assembled_root_ref,
            "adapter_hints": self.adapter_hints,
            "notes": self.notes,
        }
