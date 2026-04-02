"""Shared temporal precision types."""

from __future__ import annotations

from enum import StrEnum


class TemporalPrecision(StrEnum):
    TIMESTAMP = "timestamp"
    DATE = "date"


def parse_temporal_precision(value: str) -> TemporalPrecision | None:
    text = value.strip()
    if not text:
        return None
    try:
        return TemporalPrecision(text)
    except ValueError:
        return None
