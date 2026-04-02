"""Coinbase timestamp parsing rules."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_retail_timestamp(value: str) -> datetime:
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise ValueError(f"unsupported Coinbase retail timestamp: {value!r}")
