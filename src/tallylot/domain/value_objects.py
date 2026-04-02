"""Domain-level value helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

CANONICAL_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def quantize_decimal(value: Decimal) -> Decimal:
    return value.normalize() if value != Decimal("0") else Decimal("0")


def format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    return format(quantize_decimal(value), "f")


def parse_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return quantize_decimal(value)
    text = value.strip()
    if not text:
        return None
    return quantize_decimal(Decimal(text))


def format_timestamp(value: datetime) -> str:
    return value.strftime(CANONICAL_TIMESTAMP_FORMAT)


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), CANONICAL_TIMESTAMP_FORMAT).replace(tzinfo=UTC)


@dataclass(frozen=True)
class CsvSchema:
    header: tuple[str, ...]
