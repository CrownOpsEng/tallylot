#!/usr/bin/env python3

"""Shared schema and helper functions for the universal source-intake pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Iterable, Sequence

from script_common import (
    parse_datetime,
    parse_datetime_to_utc_naive,
    read_csv_rows,
    require_directory,
    require_file,
    source_timezone_from_filename,
    tzinfo_label,
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

DATE_FIELD_PATTERN = ("date", "time", "timestamp", "created at", "operation date", "settlement_date", "transaction_date")
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S UTC",
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
    "%d.%m.%Y %H:%M:%S",
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
    timezone_summary: dict[str, object] | None = None
    timezone_issues: list[dict[str, str]] | None = None


@dataclass(frozen=True)
class TimestampEvidence:
    value: datetime
    fmt: str
    resolution: str
    timezone_mode: str
    timezone_value: str


def source_slug(value: str) -> str:
    text = value.strip().lower().replace("&", " and ")
    chars = [char if char.isalnum() else "_" for char in text]
    slug = "".join(chars)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


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
    candidates = (
        raw_dir / "manifest.csv",
        raw_dir.parent / "manifest.csv",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def first_non_empty_csv_row(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if any(cell.strip() for cell in row):
                return row
    return []


def detect_csv_header(path: Path) -> tuple[list[str], int]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(rows[:10]):
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = row
            best_index = index
    if best_index == -1:
        return [], -1
    return best_row, best_index


def classify_file_family(path: Path, header: Sequence[str]) -> str:
    name = path.name.lower()
    header_lower = [column.strip().lower() for column in header]

    if path.suffix.lower() == ".pdf":
        return "statement_balance_pdf"
    if "coinbase pro - fills" in name:
        return "fills_csv"
    if "coinbase pro - statement" in name:
        return "transfer_statement_csv"
    if "statement - all time" in name:
        return "custodial_all_time_csv"
    if ("activity" in name or "activities" in name) and "export" in name:
        return "broker_activity_csv"
    if "monthly-statement-transactions" in name:
        return "statement_transaction_csv"
    if "portfolio" in name:
        return "portfolio_snapshot_csv"
    if "export-address-token" in name:
        return "explorer_token_transfer_csv"
    if "export-internal-tx" in name:
        return "explorer_internal_transaction_csv"
    if "export-address-nfts" in name:
        return "explorer_nft_transfer_csv"
    if "export-" in name:
        return "explorer_transaction_csv"
    if "ledgerlive-operations" in name:
        return "wallet_operation_csv"
    if "futures-trade-history" in name or "spot-trade-history" in name:
        return "fills_csv"
    if "convert-order-history" in name:
        return "convert_order_csv"
    if "deposit-history" in name and "fiat" not in name:
        return "deposit_history_csv"
    if "withdraw-history" in name and "fiat" not in name:
        return "withdrawal_history_csv"
    if "c2c-order-history" in name:
        return "p2p_order_csv"
    if "fiat-buy-history" in name:
        return "fiat_buy_csv"
    if "fiat-sell-history" in name:
        return "fiat_sell_csv"
    if "fiat-exchange-history" in name:
        return "fiat_exchange_csv"
    if "futures-transaction-history" in name:
        return "futures_transaction_csv"
    if "transaction" in name and "history" in name:
        return "custodial_transaction_csv"
    if "cash_transactions" in name:
        return "fiat_transaction_csv"
    if "crypto_transactions" in name:
        return "custodial_transaction_csv"
    if name.endswith("my_trading_history_report.csv"):
        return "derivatives_report_csv"
    if "_ft_transactions_" in name:
        return "near_ft_transaction_csv"
    if "_nft_transactions_" in name:
        return "near_nft_transaction_csv"
    if "_receipts_" in name:
        return "near_receipt_csv"
    if "_transactions_" in name and "ft_" not in name and "nft_" not in name:
        return "near_transaction_csv"
    if {"date", "pair", "addr"}.issubset(set(header_lower)):
        return "derivatives_report_csv"
    if "receipt" in header_lower and "deposit value" in header_lower:
        return "near_receipt_csv"
    if "txn hash" in header_lower and "direction" in header_lower and "token id" in header_lower:
        return "near_nft_transaction_csv"
    if "txn hash" in header_lower and "direction" in header_lower and "token" in header_lower:
        return "near_ft_transaction_csv"
    if "txn hash" in header_lower and "method" in header_lower and "deposit value" in header_lower:
        return "near_transaction_csv"
    if "statement" in header_lower and "time" in header_lower:
        return "transfer_statement_csv"
    if "trade id" in header_lower and "product" in header_lower:
        return "fills_csv"
    if "operation type" in header_lower and "operation amount" in header_lower:
        return "wallet_operation_csv"
    if "transaction hash" in header_lower:
        return "explorer_transaction_csv"
    if "activity_type" in header_lower:
        return "broker_activity_csv"
    if "type" in header_lower and "amount credited" in header_lower:
        return "custodial_transaction_csv"
    return "unknown"


def parse_candidate_timestamp(value: str, *, source_timezone: tzinfo | None = None) -> datetime | None:
    evidence = parse_candidate_timestamp_evidence(value, source_timezone=source_timezone)
    return evidence.value if evidence is not None else None


def _header_timezone_hint(header: Sequence[str], date_field: str) -> tuple[str, str]:
    joined = " | ".join(column.strip().lower() for column in header)
    field = date_field.strip().lower()
    if "utc" in field or "utc" in joined:
        return "header_utc", "UTC"
    return "", ""


def _timestamp_resolution_for_format(fmt: str) -> str:
    if "%H" not in fmt and "%I" not in fmt:
        return "date_only"
    if "%f" in fmt:
        return "subsecond"
    return "second"


def _timezone_evidence_for_format(
    fmt: str,
    parsed: datetime,
    *,
    source_timezone: tzinfo | None = None,
) -> tuple[str, str]:
    if "%z" in fmt:
        return "value_offset", tzinfo_label(parsed.tzinfo)
    if "UTC" in fmt or fmt.endswith("Z"):
        return "value_utc", "UTC"
    if _timestamp_resolution_for_format(fmt) == "date_only":
        return "date_only", ""
    if source_timezone is not None:
        return "source_timezone", tzinfo_label(source_timezone)
    return "naive", ""


def parse_candidate_timestamp_evidence(value: str, *, source_timezone: tzinfo | None = None) -> TimestampEvidence | None:
    text = value.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            parsed = parse_datetime(text, (fmt,))
        except ValueError:
            continue
        timezone_mode, timezone_value = _timezone_evidence_for_format(fmt, parsed, source_timezone=source_timezone)
        return TimestampEvidence(
            value=parse_datetime_to_utc_naive(text, (fmt,), source_timezone=source_timezone),
            fmt=fmt,
            resolution=_timestamp_resolution_for_format(fmt),
            timezone_mode=timezone_mode,
            timezone_value=timezone_value,
        )
    return None


def _finalize_timezone_metadata(
    *,
    filename: str,
    header: Sequence[str],
    date_field: str,
    parsed_values: Sequence[TimestampEvidence],
) -> tuple[str, str, str, str]:
    if not parsed_values:
        return "", "", "", ""

    resolution = parsed_values[0].resolution if len({item.resolution for item in parsed_values}) == 1 else "mixed"
    header_mode, header_value = _header_timezone_hint(header, date_field)
    filename_timezone = source_timezone_from_filename(filename)
    filename_mode = "filename_offset" if filename_timezone is not None else ""
    filename_value = tzinfo_label(filename_timezone)
    evidence_mode = parsed_values[0].timezone_mode if len({item.timezone_mode for item in parsed_values}) == 1 else "mixed"
    evidence_value = parsed_values[0].timezone_value if len({item.timezone_value for item in parsed_values}) == 1 else "mixed"

    hints = [(mode, value) for mode, value in ((header_mode, header_value), (filename_mode, filename_value), (evidence_mode, evidence_value)) if mode]
    distinct_values = {value for _, value in hints if value}
    if len(distinct_values) > 1:
        return resolution, "conflict", " | ".join(sorted(distinct_values)), "yes"

    if evidence_mode in {"value_utc", "value_offset"}:
        return resolution, evidence_mode, evidence_value, ""
    if filename_mode:
        return resolution, filename_mode, filename_value, ""
    if header_mode:
        return resolution, header_mode, header_value, ""
    return resolution, evidence_mode, evidence_value, ""


def detect_date_span_from_csv(path: Path) -> tuple[str, str, str, int, str, str, str, str]:
    header, header_index = detect_csv_header(path)
    if header_index == -1 or not header:
        return "", "", "", 0, "", "", "", ""

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        payload = list(reader)[header_index + 1 :]

    normalized_rows = [
        {header[index]: (row[index] if index < len(row) else "") for index in range(len(header))}
        for row in payload
        if any(cell.strip() for cell in row)
        and not (len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.")
    ]
    date_field = ""
    parsed_values: list[TimestampEvidence] = []
    candidates = [field for field in header if any(token in field.lower() for token in DATE_FIELD_PATTERN)]
    best_count = -1
    source_timezone = source_timezone_from_filename(path.name)
    for field in candidates:
        current = [
            parse_candidate_timestamp_evidence((row.get(field) or "").strip(), source_timezone=source_timezone)
            for row in normalized_rows
        ]
        parsed = [value for value in current if value is not None]
        if len(parsed) > best_count:
            best_count = len(parsed)
            parsed_values = parsed
            date_field = field
    if not parsed_values:
        if not normalized_rows:
            return "", "", "", 0, "", "", "", ""
        return date_field, "", "", len(normalized_rows), "", "", "", ""
    resolution, timezone_mode, timezone_value, timezone_conflict = _finalize_timezone_metadata(
        filename=path.name,
        header=header,
        date_field=date_field,
        parsed_values=parsed_values,
    )
    return (
        date_field,
        min(item.value for item in parsed_values).strftime("%Y-%m-%d %H:%M:%S"),
        max(item.value for item in parsed_values).strftime("%Y-%m-%d %H:%M:%S"),
        len(normalized_rows),
        resolution,
        timezone_mode,
        timezone_value,
        timezone_conflict,
    )


def build_file_inventory(raw_dir: Path) -> list[dict[str, str]]:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    rows: list[dict[str, str]] = []
    for path in sorted(file for file in raw_dir.iterdir() if file.is_file()):
        suffix = path.suffix.lower()
        header_preview = ""
        family = "binary_evidence"
        data_rows = ""
        date_field = ""
        min_timestamp = ""
        max_timestamp = ""
        timestamp_resolution = ""
        timezone_mode = ""
        timezone_value = ""
        timezone_conflict = ""
        if suffix == ".csv":
            header, _ = detect_csv_header(path)
            header_preview = " | ".join(header[:8])
            family = classify_file_family(path, header)
            (
                date_field,
                min_timestamp,
                max_timestamp,
                row_count,
                timestamp_resolution,
                timezone_mode,
                timezone_value,
                timezone_conflict,
            ) = detect_date_span_from_csv(path)
            data_rows = str(row_count)
        elif suffix == ".pdf":
            family = classify_file_family(path, ())
        rows.append(
            {
                "filename": path.name,
                "suffix": suffix,
                "family": family,
                "header_preview": header_preview,
                "data_rows": data_rows,
                "date_field": date_field,
                "min_timestamp": min_timestamp,
                "max_timestamp": max_timestamp,
                "timestamp_resolution": timestamp_resolution,
                "timezone_mode": timezone_mode,
                "timezone_value": timezone_value,
                "timezone_conflict": timezone_conflict,
            }
        )
    return rows


def build_source_profile(
    *,
    source: str,
    raw_dir: Path,
    adapter_name: str,
    adapter_supported: bool,
    manifest_path: Path | None = None,
) -> SourceProfile:
    raw_dir = require_directory(raw_dir.resolve(), "Raw source directory")
    manifest_path = manifest_path.resolve() if manifest_path is not None else find_manifest_for_raw_dir(raw_dir)
    manifest_rows = read_csv_rows(manifest_path) if manifest_path is not None and manifest_path.exists() else []
    fingerprint = manifest_fingerprint_from_rows(manifest_rows) if manifest_rows else stable_hash_rows(build_file_inventory(raw_dir))
    return SourceProfile(
        source=source,
        source_slug=source_slug(source),
        raw_dir=raw_dir,
        manifest_path=manifest_path,
        manifest_fingerprint=fingerprint,
        adapter=adapter_name,
        adapter_supported=adapter_supported,
        file_inventory=build_file_inventory(raw_dir),
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
