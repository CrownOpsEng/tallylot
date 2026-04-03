"""Coinbase retail export detection and matching."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.domain.models import FileInventoryEntry

RETAIL_HEADER = (
    "ID",
    "Timestamp",
    "Transaction Type",
    "Asset",
    "Quantity Transacted",
    "Price Currency",
    "Price at Transaction",
    "Subtotal",
    "Total (inclusive of fees and/or spread)",
    "Fees and/or Spread",
    "Notes",
)
RETAIL_HEADER_PREFIX = "ID,Timestamp,Transaction Type,Asset,"


def match_coinbase_inventory(
    source: str,
    raw_dir: Path,
    inventory: tuple[FileInventoryEntry, ...],
) -> int:
    if "coinbase" in source.lower():
        return 100
    if any(item.relative_path.endswith(".csv") and item.header == RETAIL_HEADER for item in inventory):
        return 100
    if any(header_for_path(path) == RETAIL_HEADER for path in raw_dir.rglob("*.csv")):
        return 100
    return 0


def retail_path(raw_dir: Path) -> Path | None:
    for path in sorted(raw_dir.rglob("*.csv")):
        if header_for_path(path) == RETAIL_HEADER:
            return path
    return None


def header_for_path(path: Path) -> tuple[str, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        lines = [line.rstrip("\n") for line in handle]
    for index, line in enumerate(lines):
        if line.startswith(RETAIL_HEADER_PREFIX):
            return tuple(next(csv.reader([line])))
        if index > 4:
            break
    return ()
