#!/usr/bin/env python3

"""Shared file inspection and historical-date inference helpers."""

from __future__ import annotations

import csv
import json
import re
import io
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Iterable, Sequence

from archive_handling import summarize_archive_members
from scope_identity import csv_scope_tokens, describe_scope_tokens, extract_scope_tokens, json_scope_tokens, token_from_header_value
from script_common import parse_datetime, parse_datetime_to_utc_naive, sniff_csv_dialect, source_timezone_from_filename, tzinfo_label


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
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S+00",
)
EXPORT_DATE_PATTERNS = (
    re.compile(r"(?<!\d)(?P<date>\d{4}-\d{2}-\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<date>\d{4}\.\d{2}\.\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(?P<date>\d{8})(?!\d)"),
)
COMPACT_TIMESTAMP_PATTERN = re.compile(r"(?<!\d)(?P<timestamp>\d{12}|\d{14})(?!\d)")
YEAR_MONTH_PATTERN = re.compile(r"(?P<year>20\d{2})[-_.](?P<month>\d{2})")
YEAR_PATTERN = re.compile(r"(?<!\d)(?P<year>20\d{2})(?!\d)")


@dataclass(frozen=True)
class TimestampEvidence:
    value: datetime
    fmt: str
    resolution: str
    timezone_mode: str
    timezone_value: str


@dataclass(frozen=True)
class HistoricalDateDecision:
    capture_id: str
    granularity: str
    basis: str
    review_required: bool = False


@dataclass(frozen=True)
class HistoricalDatePolicy:
    prefer_last_explicit: bool = True
    allow_content_span: bool = True
    allow_compact_timestamp: bool = True
    allow_year_month_context: bool = True
    allow_year_context: bool = True


@dataclass
class DateFieldStats:
    count: int = 0
    min_value: datetime | None = None
    max_value: datetime | None = None
    first_resolution: str = ""
    resolution_values: set[str] | None = None
    first_timezone_mode: str = ""
    timezone_modes: set[str] | None = None
    first_timezone_value: str = ""
    timezone_values: set[str] | None = None

    def __post_init__(self) -> None:
        if self.resolution_values is None:
            self.resolution_values = set()
        if self.timezone_modes is None:
            self.timezone_modes = set()
        if self.timezone_values is None:
            self.timezone_values = set()

    def update(self, evidence: TimestampEvidence) -> None:
        self.count += 1
        self.min_value = evidence.value if self.min_value is None else min(self.min_value, evidence.value)
        self.max_value = evidence.value if self.max_value is None else max(self.max_value, evidence.value)
        if not self.first_resolution:
            self.first_resolution = evidence.resolution
        if not self.first_timezone_mode:
            self.first_timezone_mode = evidence.timezone_mode
        if not self.first_timezone_value:
            self.first_timezone_value = evidence.timezone_value
        self.resolution_values.add(evidence.resolution)
        self.timezone_modes.add(evidence.timezone_mode)
        if evidence.timezone_value:
            self.timezone_values.add(evidence.timezone_value)


def iter_csv_rows(path: Path) -> Iterable[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.reader(handle, dialect=sniff_csv_dialect(path))


def detect_csv_header(path: Path) -> tuple[list[str], int]:
    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(iter_csv_rows(path)):
        if index >= 10:
            break
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = row
            best_index = index
    if best_index == -1:
        return [], -1
    return best_row, best_index


def detect_csv_header_from_text(text: str) -> tuple[list[str], int]:
    rows = list(csv.reader(io.StringIO(text)))
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
    header_set = set(header_lower)

    def has_all(*columns: str) -> bool:
        return set(columns).issubset(header_set)

    if path.suffix.lower() == ".pdf":
        return "statement_balance_pdf"
    if has_all("type", "buy", "cur.", "sell", "fee", "exchange", "date"):
        return "cointracking_trade_table_csv"
    if has_all("type", "buy amount", "buy cur.", "sell amount", "sell cur.", "fee amount (optional)"):
        return "cointracking_import_csv"
    if has_all("id", "timestamp", "transaction type") and ("asset" in header_set or "statement" in name):
        return "custodial_all_time_csv"
    if has_all("portfolio", "trade id", "product", "side", "created at"):
        return "fills_csv"
    if has_all("portfolio", "type", "time", "amount", "balance", "amount/balance unit"):
        return "transfer_statement_csv"
    if has_all("transaction_date", "settlement_date", "account_type", "activity_type"):
        return "broker_activity_csv"
    if has_all("date", "transaction", "description", "amount", "balance", "currency"):
        return "statement_transaction_csv"
    if has_all("operation date", "operation type", "operation amount"):
        return "wallet_operation_csv"
    if has_all("date", "pair", "addr"):
        return "derivatives_report_csv"
    if has_all("deal_id", "status", "bot", "account", "bot_id", "pair"):
        return "trading_bot_deals_csv"
    if "receipt" in header_set and "deposit value" in header_set:
        return "near_receipt_csv"
    if has_all("txn hash", "direction", "token id", "contract"):
        return "near_nft_transaction_csv"
    if has_all("txn hash", "direction", "token", "contract"):
        return "near_ft_transaction_csv"
    if has_all("txn hash", "method", "deposit value", "txn fee"):
        return "near_transaction_csv"
    if has_all("user_id", "utc_time", "account", "operation", "coin", "change", "remark"):
        return "custodial_transaction_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "tokenvalue", "tokensymbol"):
        return "explorer_token_transfer_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "token id", "quantity"):
        return "explorer_nft_transfer_csv"
    if has_all("transaction hash", "blockno", "unixtimestamp", "datetime (utc)", "parenttxfrom", "parenttxto"):
        return "explorer_internal_transaction_csv"
    if "transaction hash" in header_set and "datetime (utc)" in header_set and any(
        column.startswith("value_in(") or column.startswith("value_out(") for column in header_lower
    ):
        return "explorer_transaction_csv"
    if has_all("txhash", "blockno", "unixtimestamp", "datetime", "from", "to"):
        return "explorer_transaction_csv"
    if has_all("type", "amount credited", "asset credited", "amount debited", "asset debited"):
        return "custodial_transaction_csv"
    if has_all("date", "type", "description", "debit", "credit"):
        return "fiat_transaction_csv"
    if has_all("timestamp (utc)", "transaction description", "currency", "amount", "transaction kind"):
        return "custodial_transaction_csv"
    if has_all("time", "wallet", "pair", "sell", "buy", "status"):
        return "convert_order_csv"
    if has_all("time", "coin", "network", "amount", "address", "txid", "status"):
        return "deposit_history_csv"
    if has_all("time", "coin", "network", "amount", "fee", "address", "txid", "status"):
        return "withdrawal_history_csv"
    if has_all("order number", "order type", "asset", "fiat type", "total price", "status"):
        return "p2p_order_csv"
    if has_all("time", "method", "spend amount", "receive amount", "fee", "price", "status", "transaction id"):
        return "fiat_buy_csv"
    if has_all("method", "amount", "price", "final amount", "created time", "status", "transaction id"):
        return "fiat_exchange_csv"
    if has_all("time", "type", "amount", "asset", "symbol", "transaction id"):
        return "futures_transaction_csv"
    if has_all("time", "pair", "side", "price", "executed", "amount", "fee"):
        return "fills_csv"
    if has_all("date(utc)", "pair", "side", "price", "executed", "amount", "fee"):
        return "binance_margin_trade_csv"
    if has_all("date(utc)", "orderno", "pair", "type", "side", "order price"):
        return "binance_margin_order_csv"
    if has_all("pair", "coin", "date", "amount", "type", "status"):
        return "binance_margin_borrow_csv"
    if has_all("pair", "coin", "amount", "time", "interest type"):
        return "binance_margin_interest_csv"
    if has_all("pair", "coin", "date", "principal amount", "interest", "total"):
        return "binance_margin_repay_csv"
    if has_all("pair", "coin", "date", "margin account (in/out)", "amount"):
        return "binance_margin_transfer_csv"
    if has_all("date", "pair", "type", "side", "average", "price", "executed", "amount", "total"):
        return "binance_margin_liquidation_csv"
    if has_all("date", "pair", "coin", "amount", "to account", "bnb deducted"):
        return "binance_margin_fee_return_csv"
    if has_all("chain", "token", "amount", "value") or "portfolio" in name:
        return "portfolio_snapshot_csv"
    if "transaction" in name and "history" in name:
        return "custodial_transaction_csv"
    return "unknown"


def inspect_json_payload(path: Path) -> tuple[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "json", ""
    if isinstance(payload, dict):
        header_preview = " | ".join(str(key) for key in list(payload.keys())[:8])
        if isinstance(payload.get("metamask"), dict):
            return "metamask_state_json", header_preview
        return "json", header_preview
    return "json", type(payload).__name__


def inspect_json_scope_tokens(path: Path) -> frozenset[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    return json_scope_tokens(payload)


def inspect_archive_payload(path: Path) -> tuple[str, str, dict[str, str]]:
    summary = summarize_archive_members(path, inspect_file)
    preview = summary.get("archive_member_preview", "")
    family_candidates = [item for item in summary.get("archive_member_families", "").split(";") if item]
    if len(set(family_candidates)) == 1 and family_candidates:
        return family_candidates[0], preview, summary
    if summary.get("archive_detected_source") == "CoinTracking":
        return "cointracking_archive_bundle", preview, summary
    if summary.get("archive_detected_source") == "Binance":
        return "binance_archive_bundle", preview, summary
    return "archive_bundle", preview, summary


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


def parse_candidate_timestamp(value: str, *, source_timezone: tzinfo | None = None) -> datetime | None:
    evidence = parse_candidate_timestamp_evidence(value, source_timezone=source_timezone)
    return evidence.value if evidence is not None else None


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

    hints = [
        (mode, value)
        for mode, value in ((header_mode, header_value), (filename_mode, filename_value), (evidence_mode, evidence_value))
        if mode
    ]
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


def analyze_csv(path: Path) -> tuple[list[str], int, str, str, str, int, str, str, str, str]:
    sample_rows: list[list[str]] = []
    rows = iter_csv_rows(path)
    for _ in range(10):
        try:
            sample_rows.append(next(rows))
        except StopIteration:
            break

    best_index = -1
    best_row: list[str] = []
    for index, row in enumerate(sample_rows):
        width = len([cell for cell in row if cell.strip()])
        if width > len(best_row):
            best_row = row
            best_index = index

    header = best_row
    header_index = best_index
    if header_index == -1 or not header:
        return [], -1, "", "", "", 0, "", "", "", ""

    date_field = ""
    candidates = [field for field in header if any(token in field.lower() for token in DATE_FIELD_PATTERN)]
    source_timezone = source_timezone_from_filename(path.name)
    stats_by_field = {field: DateFieldStats() for field in candidates}
    row_count = 0

    def consume_rows(row_iter: Iterable[list[str]], *, start_index: int) -> None:
        nonlocal row_count
        for offset, row in enumerate(row_iter):
            absolute_index = start_index + offset
            if absolute_index <= header_index:
                continue
            if not any(cell.strip() for cell in row):
                continue
            if len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.":
                continue
            row_count += 1
            if not candidates:
                continue
            normalized_row = {header[index]: (row[index] if index < len(row) else "") for index in range(len(header))}
            for field in candidates:
                evidence = parse_candidate_timestamp_evidence(
                    (normalized_row.get(field) or "").strip(),
                    source_timezone=source_timezone,
                )
                if evidence is not None:
                    stats_by_field[field].update(evidence)

    consume_rows(sample_rows, start_index=0)
    consume_rows(rows, start_index=len(sample_rows))

    best_count = -1
    best_stats: DateFieldStats | None = None
    for field in candidates:
        stats = stats_by_field[field]
        if stats.count > best_count:
            best_count = stats.count
            best_stats = stats
            date_field = field

    if best_stats is None or best_stats.count == 0:
        if row_count == 0:
            return header, header_index, "", "", "", 0, "", "", "", ""
        return header, header_index, date_field, "", "", row_count, "", "", "", ""
    resolution, timezone_mode, timezone_value, timezone_conflict = _finalize_timezone_metadata(
        filename=path.name,
        header=header,
        date_field=date_field,
        parsed_values=[
            TimestampEvidence(
                value=best_stats.min_value or best_stats.max_value or datetime.min,
                fmt="",
                resolution=best_stats.first_resolution,
                timezone_mode=best_stats.first_timezone_mode,
                timezone_value=best_stats.first_timezone_value,
            )
        ]
        if len(best_stats.resolution_values) <= 1 and len(best_stats.timezone_modes) <= 1 and len(best_stats.timezone_values) <= 1
        else [
            TimestampEvidence(
                value=best_stats.min_value or datetime.min,
                fmt="",
                resolution=best_stats.first_resolution,
                timezone_mode=best_stats.first_timezone_mode,
                timezone_value=best_stats.first_timezone_value,
            ),
            TimestampEvidence(
                value=best_stats.max_value or datetime.min,
                fmt="",
                resolution=(
                    best_stats.first_resolution
                    if len(best_stats.resolution_values) <= 1
                    else "mixed"
                ),
                timezone_mode=(
                    best_stats.first_timezone_mode
                    if len(best_stats.timezone_modes) <= 1
                    else "mixed"
                ),
                timezone_value=(
                    best_stats.first_timezone_value
                    if len(best_stats.timezone_values) <= 1
                    else "mixed"
                ),
            ),
        ],
    )
    return (
        header,
        header_index,
        date_field,
        (best_stats.min_value or datetime.min).strftime("%Y-%m-%d %H:%M:%S"),
        (best_stats.max_value or datetime.min).strftime("%Y-%m-%d %H:%M:%S"),
        row_count,
        resolution,
        timezone_mode,
        timezone_value,
        timezone_conflict,
    )


def inspect_csv_scope_tokens(path: Path, *, max_rows: int = 100) -> frozenset[str]:
    try:
        header, header_index = detect_csv_header(path)
    except OSError:
        return frozenset()
    if header_index < 0 or not header:
        return frozenset()
    family = classify_file_family(path, header)
    rows: list[dict[str, str]] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle, dialect=sniff_csv_dialect(path))
            for index, row in enumerate(reader):
                if index <= header_index:
                    continue
                if not any(cell.strip() for cell in row):
                    continue
                if len(row) == 1 and row[0].strip().lower() == "no data matches the criteria.":
                    continue
                rows.append({header[column]: (row[column] if column < len(row) else "") for column in range(len(header))})
                if len(rows) >= max_rows:
                    break
    except OSError:
        return frozenset()
    tokens = set(csv_scope_tokens(rows))
    if family.startswith("explorer_"):
        for header_name in header:
            normalized_header = " ".join(header_name.strip().lower().split())
            if normalized_header not in {"from", "to", "addr", "address", "owner", "wallet"}:
                continue
            values = {row.get(header_name, "").strip() for row in rows if row.get(header_name, "").strip()}
            if len(values) != 1:
                continue
            tokens.update(token_from_header_value(header_name, next(iter(values))))
    return frozenset(tokens)


def detect_date_span_from_csv(path: Path) -> tuple[str, str, str, int, str, str, str, str]:
    (
        _header,
        _header_index,
        date_field,
        min_timestamp,
        max_timestamp,
        row_count,
        resolution,
        timezone_mode,
        timezone_value,
        timezone_conflict,
    ) = analyze_csv(path)
    return date_field, min_timestamp, max_timestamp, row_count, resolution, timezone_mode, timezone_value, timezone_conflict


def inspect_file(path: Path) -> dict[str, str]:
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
    archive_summary: dict[str, str] = {}
    path_scope_tokens = extract_scope_tokens(str(path))
    content_scope_tokens: set[str] = set()
    if suffix == ".csv":
        (
            header,
            _header_index,
            date_field,
            min_timestamp,
            max_timestamp,
            row_count,
            timestamp_resolution,
            timezone_mode,
            timezone_value,
            timezone_conflict,
        ) = analyze_csv(path)
        header_preview = " | ".join(header[:8])
        family = classify_file_family(path, header)
        data_rows = str(row_count)
        content_scope_tokens.update(inspect_csv_scope_tokens(path))
    elif suffix == ".pdf":
        family = classify_file_family(path, ())
    elif suffix == ".json":
        family, header_preview = inspect_json_payload(path)
        content_scope_tokens.update(inspect_json_scope_tokens(path))
    elif suffix in {".zip", ".tar"} or path.name.lower().endswith((".tar.gz", ".tgz")):
        family, header_preview, archive_summary = inspect_archive_payload(path)
        content_scope_tokens.update(extract_scope_tokens(archive_summary.get("archive_scope_tokens", "")))
    scope_tokens = content_scope_tokens or path_scope_tokens
    return {
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
        "path_scope_tokens": ";".join(sorted(path_scope_tokens)),
        "content_scope_tokens": ";".join(sorted(content_scope_tokens)),
        "scope_tokens": ";".join(sorted(scope_tokens)),
        "scope_preview": describe_scope_tokens(scope_tokens),
        **archive_summary,
    }


def build_file_inventory(raw_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(file for file in raw_dir.rglob("*") if file.is_file()):
        row = inspect_file(path)
        relative = str(path.relative_to(raw_dir))
        parts = path.relative_to(raw_dir).parts
        row["filename"] = relative
        row["source_path"] = relative
        row["bundle_id"] = parts[0] if len(parts) > 1 else ""
        row["bundle_type"] = "bundle" if len(parts) > 1 else "root_file"
        row["bundle_relative_path"] = str(Path(*parts[1:])) if len(parts) > 1 else path.name
        row["alias_group"] = ""
        row["collision_status"] = ""
        rows.append(row)
    return rows


def _explicit_date_matches(text: str) -> list[tuple[datetime, str]]:
    matches: list[tuple[datetime, str]] = []
    for pattern in EXPORT_DATE_PATTERNS:
        for match in pattern.finditer(text):
            date_text = match.group("date")
            try:
                if "." in date_text:
                    parsed = datetime.strptime(date_text, "%Y.%m.%d")
                elif "-" in date_text:
                    parsed = datetime.strptime(date_text, "%Y-%m-%d")
                else:
                    parsed = datetime.strptime(date_text, "%Y%m%d")
            except ValueError:
                continue
            matches.append((parsed, date_text))
    return matches


def _compact_timestamp_matches(text: str) -> list[tuple[datetime, str]]:
    matches: list[tuple[datetime, str]] = []
    for match in COMPACT_TIMESTAMP_PATTERN.finditer(text):
        value = match.group("timestamp")
        fmt = "%Y%m%d%H%M%S" if len(value) == 14 else "%Y%m%d%H%M"
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        matches.append((parsed, value))
    return matches


def infer_historical_date(
    parts: Iterable[str],
    inspection_row: dict[str, str],
    *,
    policy: HistoricalDatePolicy | None = None,
) -> HistoricalDateDecision:
    effective_policy = policy or HistoricalDatePolicy()
    texts = [part for part in parts if part]

    explicit_matches: list[tuple[datetime, str]] = []
    for text in texts:
        explicit_matches.extend(_explicit_date_matches(text))
    if explicit_matches:
        parsed, date_text = explicit_matches[-1] if effective_policy.prefer_last_explicit else explicit_matches[0]
        return HistoricalDateDecision(
            capture_id=parsed.strftime("%Y-%m"),
            granularity="month",
            basis=f"filename_or_folder:{date_text}",
        )

    if effective_policy.allow_compact_timestamp:
        compact_matches: list[tuple[datetime, str]] = []
        for text in texts:
            compact_matches.extend(_compact_timestamp_matches(text))
        if compact_matches:
            parsed, token = compact_matches[-1] if effective_policy.prefer_last_explicit else compact_matches[0]
            return HistoricalDateDecision(
                capture_id=parsed.strftime("%Y-%m"),
                granularity="month",
                basis=f"filename_or_folder:{token}",
            )

    if effective_policy.allow_year_month_context:
        year_month_matches: list[str] = []
        for text in texts:
            year_month_matches.extend(match.group(0) for match in YEAR_MONTH_PATTERN.finditer(text))
        if year_month_matches:
            token = year_month_matches[-1] if effective_policy.prefer_last_explicit else year_month_matches[0]
            match = YEAR_MONTH_PATTERN.search(token)
            assert match is not None
            return HistoricalDateDecision(
                capture_id=f"{match.group('year')}-{match.group('month')}",
                granularity="month",
                basis=f"filename_or_folder:{token}",
            )

    min_timestamp = inspection_row.get("min_timestamp", "")
    if effective_policy.allow_content_span and min_timestamp:
        parsed = datetime.strptime(min_timestamp, "%Y-%m-%d %H:%M:%S")
        return HistoricalDateDecision(
            capture_id=parsed.strftime("%Y-%m"),
            granularity="month",
            basis=f"content_span:{inspection_row.get('min_timestamp', '')}",
        )

    if effective_policy.allow_year_context:
        year_matches: list[str] = []
        for text in texts:
            year_matches.extend(match.group("year") for match in YEAR_PATTERN.finditer(text))
        if year_matches:
            year = year_matches[-1] if effective_policy.prefer_last_explicit else year_matches[0]
            return HistoricalDateDecision(
                capture_id=year,
                granularity="year",
                basis=f"filename_or_folder:{year}",
            )

    return HistoricalDateDecision(
        capture_id="review-required",
        granularity="unknown",
        basis="no_defensible_historical_date",
        review_required=True,
    )
