from __future__ import annotations

from decimal import Decimal

from crypto_reconciliation.domain.value_objects import format_decimal, parse_decimal


def test_parse_decimal_preserves_precision_without_float_rounding() -> None:
    value = parse_decimal("0.12340000")

    assert value == Decimal("0.1234")


def test_format_decimal_handles_none_and_zero() -> None:
    assert format_decimal(None) == ""
    assert format_decimal(Decimal("0")) == "0"
