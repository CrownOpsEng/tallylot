"""Profile inventory builders and CSV inspection helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.application.services.csv_inventory import (
    filename_timezone,
    format_timezone_value,
    inventory_csv_content,
    is_timestamp_field,
    parse_inventory_timestamp,
    timestamp_resolution,
    value_has_non_utc_offset,
)
from crypto_reconciliation.application.services.intake.archive import scanned_tree_files
from crypto_reconciliation.domain.models import FileInventoryEntry, IssueRecord


def build_inventory(
    raw_dir: Path,
    *,
    inspect_archives: bool,
) -> tuple[list[FileInventoryEntry], list[IssueRecord]]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"raw source directory does not exist: {raw_dir}")
    if not raw_dir.is_dir():
        raise NotADirectoryError(f"raw source path is not a directory: {raw_dir}")
    inventory: list[FileInventoryEntry] = []
    issues: list[IssueRecord] = []
    with scanned_tree_files(raw_dir, inspect_archives=inspect_archives) as scanned_tree:
        for entry in scanned_tree.files:
            header, row_count, timezone_details = inventory_file_details(entry.file_path)
            inventory.append(
                FileInventoryEntry(
                    relative_path=entry.relative_path,
                    suffix=entry.file_path.suffix.lower(),
                    size_bytes=entry.size_bytes,
                    sha256=entry.sha256,
                    source_path=str(entry.file_path),
                    archive_source_path=entry.archive_source_path,
                    archive_member_path=entry.archive_member_path,
                    row_count=row_count,
                    header_preview=" | ".join(header[:8]),
                    header=header,
                    date_field=timezone_details.date_field,
                    min_timestamp=timezone_details.min_timestamp,
                    max_timestamp=timezone_details.max_timestamp,
                    timestamp_resolution=timezone_details.timestamp_resolution,
                    timezone_mode=timezone_details.timezone_mode,
                    timezone_value=timezone_details.timezone_value,
                    timezone_conflict=timezone_details.timezone_conflict,
                )
            )
        issues.extend(
            IssueRecord(
                issue_id=f"{raw_dir.name}:{index}:{issue.kind}",
                source=str(raw_dir),
                adapter_id="scan",
                severity=issue.severity,
                kind=issue.kind,
                message=issue.message,
                raw_file=issue.relative_path,
            )
            for index, issue in enumerate(scanned_tree.issues, start=1)
        )
    return inventory, issues


def manifest_fingerprint(inventory: list[FileInventoryEntry]) -> str:
    payload = [
        {
            "relative_path": item.relative_path,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
        }
        for item in inventory
    ]
    return hashlib.sha256(_stable_text(payload).encode("utf-8")).hexdigest()


def _stable_text(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class TimezoneDetails:
    date_field: str = ""
    min_timestamp: str = ""
    max_timestamp: str = ""
    timestamp_resolution: str = ""
    timezone_mode: str = ""
    timezone_value: str = ""
    timezone_conflict: str = ""


def inventory_file_details(path: Path) -> tuple[tuple[str, ...], int | None, TimezoneDetails]:
    if path.suffix.lower() != ".csv":
        return (), None, TimezoneDetails()
    header, rows = inventory_csv_content(path)
    row_count = len(rows)
    if not header:
        return header, row_count, TimezoneDetails()
    timezone_details = csv_timezone_details(path.name, header, rows)
    return header, row_count, timezone_details


def csv_timezone_details(
    filename: str,
    header: tuple[str, ...],
    rows: list[dict[str, str]],
) -> TimezoneDetails:
    timestamp_field = next((name for name in header if is_timestamp_field(name)), "")
    if not timestamp_field:
        return TimezoneDetails()
    values = [row.get(timestamp_field, "").strip() for row in rows if row.get(timestamp_field, "").strip()]
    sample_value = values[0] if values else ""
    header_utc = "utc" in timestamp_field.lower()
    resolution = timestamp_resolution(sample_value)
    source_timezone = filename_timezone(filename)
    timezone_mode = ""
    timezone_value = ""
    timezone_conflict = ""

    if header_utc and value_has_non_utc_offset(sample_value):
        timezone_mode = "conflict"
        timezone_conflict = f"header:{timestamp_field}|value:{sample_value}"
    elif header_utc:
        timezone_mode = "header_utc"
        timezone_value = "UTC"
    elif sample_value.endswith(("Z", " UTC")):
        timezone_mode = "value_utc"
        timezone_value = "UTC"
    elif value_has_non_utc_offset(sample_value):
        timezone_mode = "value_utc"
        timezone_value = sample_value[-6:]
    elif source_timezone is not None and sample_value:
        timezone_mode = "filename_offset"
        timezone_value = format_timezone_value(source_timezone)
    elif resolution == "date_only":
        timezone_mode = "date_only"
    elif sample_value:
        timezone_mode = "naive"

    parsed_values = [
        parsed
        for value in values
        if (parsed := parse_inventory_timestamp(value, source_timezone=source_timezone)) is not None
    ]
    parsed_values.sort()
    min_timestamp = parsed_values[0].strftime("%Y-%m-%d %H:%M:%S") if parsed_values else ""
    max_timestamp = parsed_values[-1].strftime("%Y-%m-%d %H:%M:%S") if parsed_values else ""

    return TimezoneDetails(
        date_field=timestamp_field,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
        timestamp_resolution=resolution,
        timezone_mode=timezone_mode,
        timezone_value=timezone_value,
        timezone_conflict=timezone_conflict,
    )
