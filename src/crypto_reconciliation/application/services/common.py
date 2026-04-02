"""Shared service helpers."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_header_and_count(path: Path) -> tuple[tuple[str, ...], int | None]:
    if path.suffix.lower() != ".csv":
        return (), None
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        return (), 0
    return tuple(rows[0]), max(len(rows) - 1, 0)


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
