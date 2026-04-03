"""Coinbase retail CSV row loading."""

from __future__ import annotations

import csv
from pathlib import Path

from .matching import RETAIL_HEADER_PREFIX


def read_retail_rows(path: Path) -> tuple[dict[str, str], ...]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = next(index for index, line in enumerate(lines) if line.startswith(RETAIL_HEADER_PREFIX))
    reader = csv.DictReader(lines[header_index:])
    return tuple(reader)
