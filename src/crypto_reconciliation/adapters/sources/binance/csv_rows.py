"""Binance raw CSV row loading."""

from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


def is_no_data_row(row: dict[str, str]) -> bool:
    return (row.get("User ID") or "").strip() == "No data matches the criteria."
