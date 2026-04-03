#!/usr/bin/env python3

"""Shared schema and helper functions for the universal source-intake pipeline."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from script_common import parse_datetime, read_csv_rows, require_directory, require_file, write_csv_rows, write_json


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
    candidate = raw_dir.parent / "manifest.csv"
    return candidate if candidate.exists() else None


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
    if "activity" in name and "export" in name:
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


def parse_candidate_timestamp(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return parse_datetime(text, (fmt,))
        except ValueError:
            continue
    return None


def detect_date_span_from_csv(path: Path) -> tuple[str, str, str, int]:
    header, header_index = detect_csv_header(path)
    if header_index == -1 or not header:
        return "", "", "", 0

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        payload = list(reader)[header_index + 1 :]

    normalized_rows = [
        {header[index]: (row[index] if index < len(row) else "") for index in range(len(header))}
        for row in payload
        if any(cell.strip() for cell in row)
    ]
    date_field = ""
    parsed_values: list[datetime] = []
    candidates = [field for field in header if any(token in field.lower() for token in DATE_FIELD_PATTERN)]
    best_count = -1
    for field in candidates:
        current = [parse_candidate_timestamp((row.get(field) or "").strip()) for row in normalized_rows]
        parsed = [value for value in current if value is not None]
        if len(parsed) > best_count:
            best_count = len(parsed)
            parsed_values = parsed
            date_field = field
    if not parsed_values:
        return date_field, "", "", len(normalized_rows)
    return (
        date_field,
        min(parsed_values).strftime("%Y-%m-%d %H:%M:%S"),
        max(parsed_values).strftime("%Y-%m-%d %H:%M:%S"),
        len(normalized_rows),
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
        if suffix == ".csv":
            header, _ = detect_csv_header(path)
            header_preview = " | ".join(header[:8])
            family = classify_file_family(path, header)
            date_field, min_timestamp, max_timestamp, row_count = detect_date_span_from_csv(path)
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
        },
    )
    write_csv_rows(inventory_csv, list(PROFILE_INVENTORY_HEADERS), profile.file_inventory)
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
