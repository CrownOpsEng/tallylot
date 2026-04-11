from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    format_timestamp,
    parse_decimal,
    parse_temporal_value,
    parse_timestamp,
)


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


def test_format_timestamp_rejects_naive_or_non_utc_datetimes() -> None:
    with pytest.raises(ValueError, match="timestamp must be timezone-aware UTC"):
        format_timestamp(datetime.fromisoformat("2023-08-06T10:00:00"))

    with pytest.raises(ValueError, match="timestamp must be timezone-aware UTC"):
        format_timestamp(datetime.fromisoformat("2023-08-06T10:00:00-06:00"))


def test_temporal_date_precision_round_trips_through_utc_midnight() -> None:
    value = datetime(2023, 8, 6, 0, 0, 0, tzinfo=UTC)

    assert (
        format_temporal_value(
            value,
            precision=TemporalPrecision.DATE,
            label="balance target target_at",
        )
        == "2023-08-06"
    )
    assert (
        parse_temporal_value(
            "2023-08-06",
            precision=TemporalPrecision.DATE,
        )
        == value
    )


def test_format_temporal_value_rejects_non_midnight_date_precision() -> None:
    with pytest.raises(
        ValueError,
        match="balance target target_at with date precision must be midnight UTC",
    ):
        format_temporal_value(
            datetime(2023, 8, 6, 1, 0, 0, tzinfo=UTC),
            precision=TemporalPrecision.DATE,
            label="balance target target_at",
        )
