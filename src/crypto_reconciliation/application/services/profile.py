"""Source profiling service."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import cast

from crypto_reconciliation.application.dtos import ProfileRequest, ProfileResponse
from crypto_reconciliation.application.services.archive_scan import scanned_tree_files
from crypto_reconciliation.application.services.common import ensure_directory
from crypto_reconciliation.application.services.scan import ensure_output_not_within_input_tree
from crypto_reconciliation.domain.models import FileInventoryEntry, IssueRecord, SourceProfile
from crypto_reconciliation.domain.types import AdapterId, JsonValue, SourceId
from crypto_reconciliation.ports.adapters import SourceAdapter, SourceAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "raw_file",
    "raw_row_ref",
    "status",
)


class ProfileService:
    def __init__(self, registry: SourceAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
        self._artifacts = artifacts

    def execute(self, request: ProfileRequest) -> ProfileResponse:
        ensure_output_not_within_input_tree(
            request.raw_dir,
            request.output_dir,
            input_label="raw source directory",
            output_label="profile output directory",
        )
        ensure_directory(request.output_dir)
        profile = self.create_profile(
            request.source,
            request.raw_dir,
            inspect_archives=request.inspect_archives,
        )
        self.write_profile_artifacts(profile, request.output_dir)
        return ProfileResponse(
            output_dir=request.output_dir,
            adapter_id=str(profile.adapter_id),
            file_count=len(profile.file_inventory),
            supported=profile.supported,
            issue_count=len(profile.scan_issues),
        )

    def create_profile(
        self,
        source: str,
        raw_dir: Path,
        *,
        inspect_archives: bool = True,
    ) -> SourceProfile:
        inventory, scan_issues = self._build_inventory(raw_dir, inspect_archives=inspect_archives)
        adapter = self._select_adapter(source, raw_dir, tuple(inventory))
        fingerprint = self._manifest_fingerprint(inventory)
        timezone_issues = tuple(_timezone_issues(source, adapter.manifest.adapter_id, inventory))
        return SourceProfile(
            source=SourceId(source),
            raw_dir=str(raw_dir),
            adapter_id=AdapterId(str(adapter.manifest.adapter_id)),
            manifest_fingerprint=fingerprint,
            file_inventory=tuple(inventory),
            supported=adapter.manifest.supported,
            metadata={
                "display_name": adapter.manifest.display_name,
                "scan_issue_count": str(len(scan_issues)),
                "timezone_issue_count": str(len(timezone_issues)),
            },
            timezone_summary=_timezone_summary(inventory, timezone_issues),
            scan_issues=tuple(scan_issues),
            timezone_issues=timezone_issues,
        )

    def write_profile_artifacts(self, profile: SourceProfile, output_dir: Path) -> None:
        self._artifacts.write_json(output_dir / "profile.json", cast(JsonValue, profile.to_dict()))
        self._artifacts.write_rows(
            output_dir / "profile_inventory.csv",
            (
                "relative_path",
                "suffix",
                "size_bytes",
                "sha256",
                "archive_source_path",
                "archive_member_path",
                "row_count",
                "header",
                "timestamp_resolution",
                "timezone_mode",
                "timezone_value",
                "timezone_conflict",
            ),
            (
                {
                    "relative_path": entry.relative_path,
                    "suffix": entry.suffix,
                    "size_bytes": str(entry.size_bytes),
                    "sha256": entry.sha256,
                    "archive_source_path": entry.archive_source_path,
                    "archive_member_path": entry.archive_member_path,
                    "row_count": "" if entry.row_count is None else str(entry.row_count),
                    "header": "|".join(entry.header),
                    "timestamp_resolution": entry.timestamp_resolution,
                    "timezone_mode": entry.timezone_mode,
                    "timezone_value": entry.timezone_value,
                    "timezone_conflict": entry.timezone_conflict,
                }
                for entry in profile.file_inventory
            ),
        )
        self._artifacts.write_rows(
            output_dir / "profile_issues.csv",
            ISSUE_HEADER,
            (issue.to_row() for issue in profile.scan_issues),
        )
        self._artifacts.write_rows(
            output_dir / "timezone_issues.csv",
            ISSUE_HEADER,
            (issue.to_row() for issue in profile.timezone_issues),
        )

    def _build_inventory(
        self,
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
                header, row_count, timezone_details = _inventory_file_details(entry.file_path)
                inventory.append(
                    FileInventoryEntry(
                        relative_path=entry.relative_path,
                        suffix=entry.file_path.suffix.lower(),
                        size_bytes=entry.size_bytes,
                        sha256=entry.sha256,
                        archive_source_path=entry.archive_source_path,
                        archive_member_path=entry.archive_member_path,
                        row_count=row_count,
                        header=header,
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

    def _select_adapter(
        self,
        source: str,
        raw_dir: Path,
        inventory: tuple[FileInventoryEntry, ...],
    ) -> SourceAdapter:
        ranked = sorted(
            ((adapter.match(source, raw_dir, inventory), adapter) for adapter in self._registry.source_adapters),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked:
            raise ValueError("no source adapters are registered")
        score, adapter = ranked[0]
        if score <= 0:
            raise ValueError(f"no source adapter matched {source!r} at {raw_dir}")
        tied = [candidate for candidate_score, candidate in ranked if candidate_score == score]
        if len(tied) > 1:
            tied_ids = ", ".join(sorted(str(candidate.manifest.adapter_id) for candidate in tied))
            raise ValueError(f"ambiguous source adapter match for {source!r} at {raw_dir}: {tied_ids}")
        return adapter

    def _manifest_fingerprint(self, inventory: list[FileInventoryEntry]) -> str:
        payload = [
            {
                "relative_path": item.relative_path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in inventory
        ]
        return _sha256sum_from_text(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _sha256sum_from_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _TimezoneDetails:
    def __init__(
        self,
        *,
        timestamp_resolution: str = "",
        timezone_mode: str = "",
        timezone_value: str = "",
        timezone_conflict: str = "",
    ) -> None:
        self.timestamp_resolution = timestamp_resolution
        self.timezone_mode = timezone_mode
        self.timezone_value = timezone_value
        self.timezone_conflict = timezone_conflict


def _inventory_file_details(path: Path) -> tuple[tuple[str, ...], int | None, _TimezoneDetails]:
    if path.suffix.lower() != ".csv":
        return (), None, _TimezoneDetails()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        rows = list(reader)
    row_count = len(rows)
    if not header:
        return header, row_count, _TimezoneDetails()
    timezone_details = _csv_timezone_details(header, rows)
    return header, row_count, timezone_details


def _csv_timezone_details(
    header: tuple[str, ...],
    rows: list[dict[str, str]],
) -> _TimezoneDetails:
    timestamp_field = next((name for name in header if name.lower() in {"timestamp", "date", "datetime", "time"}), "")
    if not timestamp_field:
        return _TimezoneDetails()
    sample_value = next(
        (row.get(timestamp_field, "").strip() for row in rows if row.get(timestamp_field, "").strip()),
        "",
    )
    header_utc = "utc" in timestamp_field.lower()
    resolution = _timestamp_resolution(sample_value)
    timezone_mode = ""
    timezone_value = ""
    timezone_conflict = ""

    if header_utc and _value_has_non_utc_offset(sample_value):
        timezone_mode = "conflict"
        timezone_conflict = f"header:{timestamp_field}|value:{sample_value}"
    elif header_utc:
        timezone_mode = "header_utc"
        timezone_value = "UTC"
    elif sample_value.endswith(("Z", " UTC")):
        timezone_mode = "value_utc"
        timezone_value = "UTC"
    elif _value_has_non_utc_offset(sample_value):
        timezone_mode = "value_utc"
        timezone_value = sample_value[-6:]
    elif resolution == "date":
        timezone_mode = "date_only"
    elif sample_value:
        timezone_mode = "naive"

    return _TimezoneDetails(
        timestamp_resolution=resolution,
        timezone_mode=timezone_mode,
        timezone_value=timezone_value,
        timezone_conflict=timezone_conflict,
    )


def _timestamp_resolution(value: str) -> str:
    if not value:
        return ""
    if len(value.strip()) == 10 and value.count("-") == 2:
        return "date"
    if ":" in value:
        return "second"
    return "unknown"


def _value_has_non_utc_offset(value: str) -> bool:
    stripped = value.strip()
    return len(stripped) >= 6 and stripped[-6] in {"+", "-"} and stripped[-3] == ":"


def _timezone_issues(
    source: str,
    adapter_id: AdapterId,
    inventory: list[FileInventoryEntry],
) -> list[IssueRecord]:
    issues: list[IssueRecord] = []
    for item in inventory:
        if item.timezone_conflict:
            issues.append(
                IssueRecord(
                    issue_id=f"{source}:{item.relative_path}:timezone_conflict",
                    source=source,
                    adapter_id=str(adapter_id),
                    severity="high",
                    kind="timezone_conflict",
                    message=(
                        "The file exposes conflicting timezone provenance and must be reviewed before normalization."
                    ),
                    raw_file=item.relative_path,
                )
            )
    return issues


def _timezone_summary(
    inventory: list[FileInventoryEntry],
    timezone_issues: tuple[IssueRecord, ...],
) -> dict[str, object]:
    modes: dict[str, int] = {}
    timestamped_files = 0
    for item in inventory:
        if not item.timezone_mode:
            continue
        timestamped_files += 1
        modes[item.timezone_mode] = modes.get(item.timezone_mode, 0) + 1
    return {
        "timestamped_file_count": timestamped_files,
        "timezone_issue_count": len(timezone_issues),
        "modes": modes,
    }
