#!/usr/bin/env python3

"""Shared helpers for lightweight repo scripts."""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path
from typing import Iterable


DEFAULT_VERIFICATION_EXPORTS = (
    "Validate Transactions",
    "Missing Transactions",
    "Duplicate Transactions",
    "Current Balance",
    "Balance by Exchange",
)


def require_directory(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"{label} is not a directory: {path}")
    return path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


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


def write_json(path: Path, payload: object, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
