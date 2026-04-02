#!/usr/bin/env python3

"""Shared schema and helper functions for the universal source-intake pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

from inspection import (
    TimestampEvidence,
    build_file_inventory,
    classify_file_family,
    detect_csv_header,
    detect_date_span_from_csv,
    inspect_json_payload,
    parse_candidate_timestamp,
    parse_candidate_timestamp_evidence,
)
from script_common import (
    find_required_csv_exports,
    read_csv_rows,
    require_directory,
    require_file,
    source_timezone_from_filename,
    write_csv_rows,
    write_json,
)


CANONICAL_EVENT_HEADERS = (
    "event_id",
    "source",
    "adapter",
    "account",
    "wallet",
    "raw_file",
    "raw_row_ref",
    "timestamp",
    "event_kind",
    "asset_in",
    "amount_in",
    "asset_out",
    "amount_out",
    "fee_asset",
    "fee_amount",
    "tx_hash",
    "description",
    "confidence",
    "status",
    "render_type",
    "render_exchange",
    "render_group",
    "render_comment",
    "render_comment_mode",
    "render_tx_id",
    "render_tx_id_mode",
    "render_allowed_types",
    "render_match_window_seconds",
    "render_fee_tolerance",
    "render_notes",
)

CANONICAL_BALANCE_HEADERS = (
    "source",
    "account",
    "wallet",
    "balance_kind",
    "asset",
    "quantity",
    "staked_quantity",
    "value_amount",
    "value_currency",
    "price_amount",
    "price_currency",
    "as_of",
    "pdf_file",
    "notes",
)

EXCEPTION_HEADERS = (
    "manifest_fingerprint",
    "event_id",
    "source",
    "adapter",
    "raw_file",
    "raw_row_ref",
    "exception_kind",
    "message",
    "status",
    "resolution_status",
    "resolution_note",
)

PROFILE_INVENTORY_HEADERS = (
    "filename",
    "suffix",
    "family",
    "header_preview",
    "data_rows",
    "date_field",
    "min_timestamp",
    "max_timestamp",
    "timestamp_resolution",
    "timezone_mode",
    "timezone_value",
    "timezone_conflict",
)

TIMEZONE_ISSUE_HEADERS = (
    "filename",
    "family",
    "date_field",
    "timestamp_resolution",
    "timezone_mode",
    "timezone_value",
    "issue_kind",
    "message",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_INVENTORY_PATH = REPO_ROOT / "03_analysis" / "issues" / "source_inventory.csv"
CANONICAL_BASELINE_EXPORT_DIR = REPO_ROOT / "01_raw_exports" / "cointracking" / "2023-08-05_full_export"
CANONICAL_BASELINE_REQUIRED_FILES = {"trade_table": "Trade Table"}
CANONICAL_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
REPO_PROJECT_WINDOW_END = "2025-12-31 23:59:59"


@dataclass(frozen=True)
class SourceProfile:
    source: str
    source_slug: str
    raw_dir: Path
    manifest_path: Path | None
    manifest_fingerprint: str
    adapter: str
    adapter_supported: bool
    file_inventory: list[dict[str, str]]
    normalization_hints: dict[str, object] | None = None
    timezone_summary: dict[str, object] | None = None
    timezone_issues: list[dict[str, str]] | None = None


def source_slug(value: str) -> str:
    text = value.strip().lower().replace("&", " and ")
    chars = [char if char.isalnum() else "_" for char in text]
    slug = "".join(chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def parse_canonical_timestamp(value: str, *, label: str = "timestamp") -> datetime:
    text = value.strip()
    if not text:
        raise ValueError(f"Blank {label} is not allowed")
    try:
        return datetime.strptime(text, CANONICAL_TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"{label} must use {CANONICAL_TIMESTAMP_FORMAT}; got {value!r}"
        ) from exc


def stable_hash_rows(rows: Iterable[dict[str, str]]) -> str:
    payload = json.dumps(list(rows), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def manifest_fingerprint_from_rows(rows: list[dict[str, str]]) -> str:
    ordered = sorted(
        (
            {
                "filename": row.get("filename", ""),
                "size_bytes": row.get("size_bytes", ""),
                "sha256": row.get("sha256", ""),
            }
            for row in rows
        ),
        key=lambda item: item["filename"],
    )
    return stable_hash_rows(ordered)


def find_manifest_for_raw_dir(raw_dir: Path) -> Path | None:
    candidate = raw_dir / "manifest.csv"
    return candidate if candidate.exists() else None


@lru_cache(maxsize=1)
def repo_source_inventory_rows() -> tuple[dict[str, str], ...]:
    if not SOURCE_INVENTORY_PATH.exists():
        return ()
    return tuple(read_csv_rows(SOURCE_INVENTORY_PATH))


@lru_cache(maxsize=1)
def repo_baseline_cutoff_timestamp() -> str:
    if not CANONICAL_BASELINE_EXPORT_DIR.exists():
        return ""
    try:
        trade_table = find_required_csv_exports(
            CANONICAL_BASELINE_EXPORT_DIR,
            CANONICAL_BASELINE_REQUIRED_FILES,
            "Canonical baseline export directory",
        )["trade_table"]
    except (FileNotFoundError, ValueError):
        return ""
    dated_rows = [row["Date"] for row in read_csv_rows(trade_table) if row.get("Date")]
    if not dated_rows:
        return ""
    return max(datetime.strptime(value, CANONICAL_TIMESTAMP_FORMAT) for value in dated_rows).strftime(CANONICAL_TIMESTAMP_FORMAT)


@lru_cache(maxsize=1)
def repo_project_window_start() -> str:
    baseline_cutoff = repo_baseline_cutoff_timestamp()
    if not baseline_cutoff:
        return ""
    return (parse_canonical_timestamp(baseline_cutoff, label="baseline cutoff") + timedelta(seconds=1)).strftime(
        CANONICAL_TIMESTAMP_FORMAT
    )


def repo_source_inventory_row(source: str, raw_dir: Path) -> dict[str, str] | None:
    target_dir = raw_dir.resolve()
    target_slug = source_slug(source)
    for row in repo_source_inventory_rows():
        capture_path = (row.get("capture_path") or "").strip()
        if not capture_path or source_slug(row.get("source", "")) != target_slug:
            continue
        if (REPO_ROOT / capture_path).resolve() == target_dir:
            return row
    return None


def repo_normalization_hints_for_source(source: str, raw_dir: Path) -> dict[str, object]:
    row = repo_source_inventory_row(source, raw_dir)
    hints: dict[str, object] = {}
    if row is not None:
        if row.get("capture_path"):
            hints["repo_capture_path"] = row["capture_path"]
        if row.get("export_window_start"):
            hints["capture_window_start"] = row["export_window_start"]
        if row.get("export_window_end"):
            hints["capture_window_end"] = row["export_window_end"]
    if row is not None:
        baseline_cutoff = repo_baseline_cutoff_timestamp()
        if baseline_cutoff:
            hints["project_baseline_cutoff_timestamp"] = baseline_cutoff
    if row is not None and (row.get("status") or "").strip() == "capture_complete":
        project_window_start = repo_project_window_start()
        if project_window_start:
            hints["project_window_start"] = project_window_start
        hints["project_window_end"] = REPO_PROJECT_WINDOW_END
    return hints


def normalization_window_from_hints(
    hints: dict[str, object] | None,
    *,
    start_key: str = "normalization_window_start",
    end_key: str = "normalization_window_end",
) -> tuple[str, str]:
    values = hints or {}
    start = values.get(start_key, "")
    end = values.get(end_key, "")
    return (start if isinstance(start, str) else "", end if isinstance(end, str) else "")


def filter_rows_by_timestamp_window(
    rows: Sequence[dict[str, str]],
    *,
    timestamp_key: str,
    window_start: str = "",
    window_end: str = "",
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not window_start and not window_end:
        return list(rows), []

    start_dt = parse_canonical_timestamp(window_start, label="window_start") if window_start else None
    end_dt = parse_canonical_timestamp(window_end, label="window_end") if window_end else None
    included: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        timestamp_text = (row.get(timestamp_key) or "").strip()
        timestamp_dt = parse_canonical_timestamp(timestamp_text, label=timestamp_key)
        if start_dt is not None and timestamp_dt < start_dt:
            excluded.append(row)
            continue
        if end_dt is not None and timestamp_dt > end_dt:
            excluded.append(row)
            continue
        included.append(row)
    return included, excluded


def build_source_profile(
    *,
    source: str,
    raw_dir: Path,
    adapter_name: str,
    adapter_supported: bool,
    manifest_path: Path | None = None,
    normalization_hints: dict[str, object] | None = None,
) -> SourceProfile:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    manifest_path = manifest_path.resolve() if manifest_path is not None else find_manifest_for_raw_dir(raw_dir)
    manifest_rows = read_csv_rows(manifest_path) if manifest_path is not None and manifest_path.exists() else []
    fingerprint = manifest_fingerprint_from_rows(manifest_rows) if manifest_rows else stable_hash_rows(build_file_inventory(raw_dir))
    merged_hints = repo_normalization_hints_for_source(source, raw_dir)
    if normalization_hints:
        merged_hints.update(normalization_hints)
    return SourceProfile(
        source=source,
        source_slug=source_slug(source),
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        manifest_fingerprint=fingerprint,
        adapter=adapter_name,
        adapter_supported=adapter_supported,
        file_inventory=build_file_inventory(raw_dir),
        normalization_hints=merged_hints,
    )


def write_profile_artifacts(out_dir: Path, profile: SourceProfile) -> tuple[Path, Path]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_json = out_dir / "profile.json"
    inventory_csv = out_dir / "profile_inventory.csv"
    timezone_issues_csv = out_dir / "timezone_issues.csv"
    timezone_summary = profile.timezone_summary or {"status": "not_checked", "issue_count": 0}
    timezone_issues = profile.timezone_issues or []
    write_json(
        profile_json,
        {
            "source": profile.source,
            "source_slug": profile.source_slug,
            "raw_dir": str(profile.raw_dir),
            "manifest_path": str(profile.manifest_path) if profile.manifest_path is not None else "",
            "manifest_fingerprint": profile.manifest_fingerprint,
            "adapter": profile.adapter,
            "adapter_supported": profile.adapter_supported,
            "file_count": len(profile.file_inventory),
            "file_inventory": profile.file_inventory,
            "family_counts": summarize_family_counts(profile.file_inventory),
            "normalization_hints": profile.normalization_hints or {},
            "timezone_summary": timezone_summary,
            "timezone_issue_count": len(timezone_issues),
            "timezone_issues_path": str(timezone_issues_csv),
        },
    )
    write_csv_rows(inventory_csv, list(PROFILE_INVENTORY_HEADERS), profile.file_inventory)
    write_csv_rows(timezone_issues_csv, list(TIMEZONE_ISSUE_HEADERS), timezone_issues)
    return profile_json, inventory_csv


def summarize_family_counts(rows: Sequence[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["family"]] += 1
    return dict(sorted(counts.items()))


def read_profile(path: Path) -> dict[str, object]:
    path = require_file(path.resolve(), "Profile JSON")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_canonical_event_row(row: dict[str, str]) -> None:
    missing = [header for header in CANONICAL_EVENT_HEADERS if header not in row]
    if missing:
        raise ValueError(f"Canonical event row missing required headers: {', '.join(missing)}")
    for field in ("event_id", "source", "timestamp", "event_kind", "confidence", "status"):
        if not str(row.get(field, "")).strip():
            raise ValueError(f"Canonical event row has blank required field: {field}")


def validate_canonical_balance_row(row: dict[str, str]) -> None:
    missing = [header for header in CANONICAL_BALANCE_HEADERS if header not in row]
    if missing:
        raise ValueError(f"Canonical balance row missing required headers: {', '.join(missing)}")
