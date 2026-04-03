#!/usr/bin/env python3

"""Shared helpers for lightweight repo scripts."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from decimal import Decimal
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_VERIFICATION_EXPORTS = (
    "Validate Transactions",
    "Missing Transactions",
    "Duplicate Transactions",
    "Current Balance",
    "Balance by Exchange",
)

CANONICAL_TIMEZONE = "UTC"
COINTRACKING_IMPORT_TIMEZONE = "UTC"

UTC_LABEL_PATTERN = re.compile(r"\(UTC(?P<offset>[^)]*)\)")
SUPPORTED_CSV_DELIMITERS = ",;\t"

COINTRACKING_FILE_HEADERS = (
    "Type",
    "Buy",
    "Cur.",
    "Sell",
    "Cur.",
    "Fee",
    "Cur.",
    "Exchange",
    "Group",
    "Comment",
    "Date",
    "Tx-ID",
)

COINTRACKING_HEADERS = (
    "Type",
    "Buy",
    "Buy Cur.",
    "Sell",
    "Sell Cur.",
    "Fee",
    "Fee Cur.",
    "Exchange",
    "Group",
    "Comment",
    "Date",
    "Tx-ID",
)

COINTRACKING_INDEX = {
    "Type": 0,
    "Buy": 1,
    "Buy Cur.": 2,
    "Sell": 3,
    "Sell Cur.": 4,
    "Fee": 5,
    "Fee Cur.": 6,
    "Exchange": 7,
    "Group": 8,
    "Comment": 9,
    "Date": 10,
    "Tx-ID": 11,
}


def require_directory(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"{label} is not a directory: {path}")
    return path


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{label} is not a file: {path}")
    return path


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sniff_csv_dialect(path: Path) -> csv.Dialect:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(8192)
    try:
        return csv.Sniffer().sniff(sample, delimiters=SUPPORTED_CSV_DELIMITERS)
    except csv.Error:
        return csv.get_dialect("excel")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, dialect=sniff_csv_dialect(path)))


def find_matching_csv_files(export_dir: Path, marker: str) -> list[Path]:
    return sorted(
        path
        for path in export_dir.iterdir()
        if path.is_file() and marker in path.name and path.suffix.lower() == ".csv"
    )


def find_required_csv_exports(
    export_dir: Path,
    required_files: dict[str, str],
    directory_label: str,
) -> dict[str, Path]:
    export_dir = require_directory(export_dir.resolve(), directory_label)
    files = {}
    for key, marker in required_files.items():
        matches = find_matching_csv_files(export_dir, marker)
        if not matches:
            raise FileNotFoundError(f"Missing required export containing {marker!r} in {export_dir}")
        if len(matches) > 1:
            match_names = ", ".join(path.name for path in matches)
            raise ValueError(f"Ambiguous export for {marker!r} in {export_dir}: {match_names}")
        files[key] = matches[0]
    return files


def decimal_text(value: Decimal, places: str = "0.00000000") -> str:
    return format(value.quantize(Decimal(places)), "f")


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text == "-":
        return None
    text = text.replace("$", "").replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    return Decimal(text)


def decimal_or_zero(value: str | None) -> Decimal:
    parsed = parse_decimal(value)
    return parsed if parsed is not None else Decimal("0")


def parse_datetime(value: str, formats: Sequence[str]) -> datetime:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    format_list = ", ".join(formats)
    raise ValueError(f"Unable to parse datetime {value!r}; expected one of: {format_list}")


def _format_implies_utc(fmt: str) -> bool:
    return "%z" not in fmt and ("UTC" in fmt or fmt.endswith("Z"))


def parse_utc_offset_label(value: str) -> tzinfo:
    text = value.strip()
    if text.startswith(("+", "-")) and len(text) > 1 and text[1] in "+-":
        text = text[1:]
    if text in {"", "0", "+0", "-0", "+00", "-00", "+00:00", "-00:00"}:
        return timezone.utc
    match = re.fullmatch(r"(?P<sign>[+-]?)(?P<hours>\d{1,2})(?::?(?P<minutes>\d{2}))?", text)
    if match is None:
        raise ValueError(f"Unsupported UTC offset label: {value!r}")
    sign = -1 if match.group("sign") == "-" else 1
    hours = int(match.group("hours"))
    minutes = int(match.group("minutes") or "0")
    delta = timedelta(hours=hours, minutes=minutes) * sign
    return timezone(delta)


def source_timezone_from_filename(filename: str) -> tzinfo | None:
    match = UTC_LABEL_PATTERN.search(filename)
    if match is None:
        return None
    return parse_utc_offset_label(match.group("offset"))


def tzinfo_label(value: tzinfo | None) -> str:
    if value is None:
        return ""
    zone_key = getattr(value, "key", "")
    if zone_key:
        return str(zone_key)
    offset = value.utcoffset(datetime(2000, 1, 1))
    if offset is None or offset == timedelta(0):
        return "UTC"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def coerce_datetime_to_utc_naive(value: datetime, *, source_timezone: tzinfo | None = None) -> datetime:
    if value.tzinfo is None:
        if source_timezone is None:
            return value
        value = value.replace(tzinfo=source_timezone)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def parse_datetime_to_utc_naive(
    value: str,
    formats: Sequence[str],
    *,
    source_timezone: tzinfo | None = None,
) -> datetime:
    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        implied_timezone = timezone.utc if _format_implies_utc(fmt) else source_timezone
        return coerce_datetime_to_utc_naive(parsed, source_timezone=implied_timezone)
    format_list = ", ".join(formats)
    raise ValueError(f"Unable to parse datetime {value!r}; expected one of: {format_list}")


def normalize_whitespace(value: str | None) -> str:
    return " ".join((value or "").split())


def extract_pdf_text(pdf_path: Path) -> str:
    pdf_path = require_file(pdf_path.resolve(), "PDF file")
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def write_csv_rows(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[dict[str, object]],
    *,
    encoding: str = "utf-8",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_cointracking_rows(path: Path, extra_headers: Sequence[str] = ()) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header = [*COINTRACKING_HEADERS, *extra_headers]
    require_file(path.resolve(), "CoinTracking CSV")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        actual_header = next(reader, [])
        expected_prefix = list(COINTRACKING_FILE_HEADERS)
        expected_with_lpn = [
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur.",
            "Fee",
            "Cur.",
            "Exchange",
            "Group",
            "Comment",
            "Date",
            "LPN",
            "Tx-ID",
        ]
        has_lpn = actual_header[: len(expected_with_lpn)] == expected_with_lpn
        if not has_lpn and actual_header[: len(expected_prefix)] != expected_prefix:
            raise ValueError(f"Unexpected CoinTracking header in {path}: {actual_header}")
        for raw_row in reader:
            if not any(cell.strip() for cell in raw_row):
                continue
            if has_lpn:
                raw_row = raw_row[:11] + raw_row[12:]
            padded = raw_row + [""] * (len(header) - len(raw_row))
            rows.append(dict(zip(header, padded[: len(header)])))
    return rows


def write_cointracking_rows(
    path: Path,
    rows: Iterable[dict[str, object]],
    *,
    extra_headers: Sequence[str] = (),
    encoding: str = "utf-8",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = [*COINTRACKING_HEADERS, *extra_headers]
    file_header = [*COINTRACKING_FILE_HEADERS, *extra_headers]
    with path.open("w", newline="", encoding=encoding) as handle:
        writer = csv.writer(handle)
        writer.writerow(file_header)
        for row in rows:
            writer.writerow([row.get(column, "") for column in header])


def write_json(path: Path, payload: object, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
