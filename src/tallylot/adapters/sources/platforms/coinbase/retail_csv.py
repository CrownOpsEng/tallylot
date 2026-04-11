"""Coinbase retail CSV row loading."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.support import read_csv_rows


def read_retail_rows(path: Path) -> tuple[dict[str, str], ...]:
    return read_csv_rows(path)
