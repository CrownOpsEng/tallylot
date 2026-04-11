"""EVM explorer parsing helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.value_objects import parse_decimal


def parse_amount(row: dict[str, str], prefix: str) -> Decimal:
    value = next(
        (text for field, text in row.items() if field.startswith(f"{prefix}(")), ""
    )
    parsed = parse_decimal(value.replace(",", "").strip())
    return parsed or Decimal("0")


def parse_utc_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(f"{value}+00:00").astimezone(UTC)
    except ValueError:
        return None
