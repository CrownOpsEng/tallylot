#!/usr/bin/env python3

"""Unwrap Binance download-center zip exports into CSV evidence and combined working files."""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zipfile
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Sequence

from source_manifest import validate_source_dir
from script_common import parse_datetime_to_utc_naive, source_timezone_from_filename, write_csv_rows


ZIP_EXPORT_PATTERN = re.compile(
    r"^(?P<family>.+)-(?P<exported_at>\d{12}\(UTC[^)]*\))(?:_(?P<token>[^.]+))?(?: \(\d+\))?$"
)
YEAR_SPLIT_PATTERN = re.compile(r"^(?P<family>.+?) (?P<year>\d{4})$")
DATE_FIELD_PATTERN = re.compile(r"(date|time)", re.IGNORECASE)
NO_DATA_SENTINEL = "No data matches the criteria."
DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--normalized-dir", type=Path)
    parser.add_argument("--delete-zips", action="store_true")
    return parser.parse_args(argv)


def parse_timestamp(value: str | None, *, source_timezone: tzinfo | None = None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    text = re.sub(r"\(UTC[^)]*\)$", "", text).strip()
    for fmt in DATE_FORMATS:
        try:
            return parse_datetime_to_utc_naive(text, (fmt,), source_timezone=source_timezone)
        except ValueError:
            continue
    return None


def is_no_data_row(row: dict[str, str | None]) -> bool:
    values = [str(value).strip() for value in row.values() if value not in (None, "")]
    return values == [NO_DATA_SENTINEL]


def family_from_name(path: Path) -> str:
    stem = path.stem
    zip_match = ZIP_EXPORT_PATTERN.match(stem)
    if zip_match:
        return zip_match.group("family")
    year_match = YEAR_SPLIT_PATTERN.match(stem)
    if year_match:
        return year_match.group("family")
    return stem


def safe_slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return slug or "binance_export"


def extract_zip(zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"Expected exactly one file in {zip_path}, found {len(members)}")
        member = members[0]
        payload = archive.read(member)
    output_path = zip_path.with_suffix(Path(member).suffix or ".csv")
    if output_path.exists():
        if output_path.read_bytes() != payload:
            raise FileExistsError(f"Refusing to overwrite differing file: {output_path}")
        return output_path
    output_path.write_bytes(payload)
    return output_path


def read_csv_payload(path: Path) -> tuple[list[str], list[dict[str, str]], bool]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows: list[dict[str, str]] = []
        saw_no_data = False
        for raw_row in reader:
            row = {key: (value or "") for key, value in raw_row.items()}
            if not any(value.strip() for value in row.values()):
                continue
            if is_no_data_row(row):
                saw_no_data = True
                continue
            rows.append(row)
    return fieldnames, rows, saw_no_data


def detect_date_span(
    fieldnames: list[str],
    rows: list[dict[str, str]],
    *,
    source_timezone: tzinfo | None = None,
) -> tuple[str, str, str]:
    best_field = ""
    best_values: list[datetime] = []
    for field in fieldnames:
        if not DATE_FIELD_PATTERN.search(field):
            continue
        values = [parse_timestamp(row.get(field), source_timezone=source_timezone) for row in rows]
        parsed = [value for value in values if value is not None]
        if len(parsed) > len(best_values):
            best_field = field
            best_values = parsed
    if not best_values:
        return "", "", ""
    return (
        best_field,
        min(best_values).strftime("%Y-%m-%d %H:%M:%S"),
        max(best_values).strftime("%Y-%m-%d %H:%M:%S"),
    )


def build_inventory_rows(source_dir: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(source_dir.glob("*.csv")):
        fieldnames, data_rows, saw_no_data = read_csv_payload(path)
        source_timezone = source_timezone_from_filename(path.name)
        date_field, min_ts, max_ts = detect_date_span(fieldnames, data_rows, source_timezone=source_timezone)
        rows.append(
            {
                "filename": path.name,
                "family": family_from_name(path),
                "data_rows": len(data_rows),
                "empty_export": "yes" if saw_no_data and not data_rows else "no",
                "date_field": date_field,
                "min_timestamp": min_ts,
                "max_timestamp": max_ts,
            }
        )
    return rows
def build_combined_outputs(source_dir: Path, normalized_dir: Path) -> list[dict[str, object]]:
    grouped: dict[str, list[Path]] = {}
    for path in sorted(source_dir.glob("*.csv")):
        grouped.setdefault(family_from_name(path), []).append(path)

    combined_dir = normalized_dir / "binance" / "combined"
    summary_rows = []
    for family, files in sorted(grouped.items()):
        if len(files) < 2:
            continue
        union_fields: list[str] = []
        combined_rows: list[dict[str, str]] = []
        empty_files = 0
        for path in files:
            fieldnames, data_rows, saw_no_data = read_csv_payload(path)
            if saw_no_data and not data_rows:
                empty_files += 1
            for field in fieldnames:
                if field and field not in union_fields:
                    union_fields.append(field)
            for row in data_rows:
                combined_row = {"source_file": path.name}
                combined_row.update(row)
                combined_rows.append(combined_row)
        output_name = f"{safe_slug(family)}_combined.csv"
        output_path = combined_dir / output_name
        write_csv_rows(output_path, ["source_file", *union_fields], combined_rows)
        summary_rows.append(
            {
                "family": family,
                "file_count": len(files),
                "empty_exports": empty_files,
                "data_rows": len(combined_rows),
                "combined_path": str(output_path.relative_to(normalized_dir.parents[1])),
            }
        )

    if summary_rows:
        write_csv_rows(
            normalized_dir / "binance" / "combined_summary.csv",
            ["family", "file_count", "empty_exports", "data_rows", "combined_path"],
            summary_rows,
        )
    return summary_rows


def unwrap_binance_exports(
    source_dir: Path,
    *,
    normalized_dir: Path | None = None,
    delete_zips: bool = False,
) -> dict[str, object]:
    source_dir = validate_source_dir(source_dir)
    extracted = []
    for zip_path in sorted(source_dir.glob("*.zip")):
        output_path = extract_zip(zip_path)
        extracted.append({"zip_file": zip_path.name, "csv_file": output_path.name})
        if delete_zips:
            zip_path.unlink()

    inventory_rows = build_inventory_rows(source_dir)
    write_csv_rows(
        source_dir.parent / "raw_csv_inventory.csv",
        ["filename", "family", "data_rows", "empty_export", "date_field", "min_timestamp", "max_timestamp"],
        inventory_rows,
    )

    combined_rows: list[dict[str, object]] = []
    if normalized_dir is not None:
        combined_rows = build_combined_outputs(source_dir, normalized_dir.resolve())

    latest = max((row["max_timestamp"] for row in inventory_rows if row["max_timestamp"]), default="")
    earliest = min((row["min_timestamp"] for row in inventory_rows if row["min_timestamp"]), default="")
    return {
        "zip_files_processed": len(extracted),
        "csv_inventory_rows": len(inventory_rows),
        "combined_files_written": len(combined_rows),
        "earliest_timestamp": earliest,
        "latest_timestamp": latest,
        "extracted": extracted,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = unwrap_binance_exports(
        args.source_dir,
        normalized_dir=args.normalized_dir,
        delete_zips=args.delete_zips,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
