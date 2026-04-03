"""Coinbase timestamp parsing rules."""

from __future__ import annotations

from datetime import UTC, datetime


def parse_retail_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
