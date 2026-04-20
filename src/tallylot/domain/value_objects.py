"""Domain-level value helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .temporal import TemporalPrecision

CANONICAL_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
CANONICAL_DATE_FORMAT = "%Y-%m-%d"


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


def require_utc_datetime(value: datetime, *, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be timezone-aware UTC")
    return value.astimezone(UTC)


def format_timestamp(value: datetime) -> str:
    return require_utc_datetime(value, label="timestamp").strftime(
        CANONICAL_TIMESTAMP_FORMAT
    )


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), CANONICAL_TIMESTAMP_FORMAT).replace(
        tzinfo=UTC
    )


def require_temporal_datetime(
    value: datetime,
    *,
    precision: TemporalPrecision,
    label: str,
) -> datetime:
    normalized = require_utc_datetime(value, label=label)
    if precision is TemporalPrecision.DATE and normalized.time() != datetime.min.time():
        raise ValueError(f"{label} with date precision must be midnight UTC")
    return normalized


def format_temporal_value(
    value: datetime, *, precision: TemporalPrecision, label: str
) -> str:
    normalized = require_temporal_datetime(value, precision=precision, label=label)
    if precision is TemporalPrecision.TIMESTAMP:
        return normalized.strftime(CANONICAL_TIMESTAMP_FORMAT)
    return normalized.strftime(CANONICAL_DATE_FORMAT)


def parse_temporal_value(value: str, *, precision: TemporalPrecision) -> datetime:
    text = value.strip()
    if precision is TemporalPrecision.TIMESTAMP:
        return parse_timestamp(text)
    return datetime.strptime(text, CANONICAL_DATE_FORMAT).replace(tzinfo=UTC)


@dataclass(frozen=True)
class CsvSchema:
    header: tuple[str, ...]
