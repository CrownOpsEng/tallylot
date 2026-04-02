from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp, parse_decimal, parse_timestamp


def test_parse_decimal_preserves_precision_without_float_rounding() -> None:
    value = parse_decimal("0.12340000")

    assert value == Decimal("0.1234")


def test_format_decimal_handles_none_and_zero() -> None:
    assert format_decimal(None) == ""
    assert format_decimal(Decimal("0")) == "0"


def test_parse_timestamp_round_trips_canonical_text() -> None:
    value = "2023-08-06 10:00:00"

    assert parse_timestamp(value) == datetime(2023, 8, 6, 10, 0, 0, tzinfo=UTC)
    assert format_timestamp(parse_timestamp(value)) == value
