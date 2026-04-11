from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tallylot.application.balances.targets import parse_target_time_values
from tallylot.domain.temporal import TemporalPrecision


def test_parse_target_time_values_defaults_date_only_to_midnight_utc() -> None:
    assert parse_target_time_values(("2025-12-30",)) == (
        (
            datetime(2025, 12, 30, 0, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )


def test_parse_target_time_values_applies_timezone_to_date_only_values() -> None:
    assert parse_target_time_values(
        ("2025-12-30",),
        timezone_value="America/Denver",
    ) == (
        (
            datetime(2025, 12, 30, 7, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )


def test_parse_target_time_values_applies_timezone_to_naive_timestamps() -> None:
    assert parse_target_time_values(
        ("2025-12-30 00:00:00",),
        timezone_value="America/Denver",
    ) == (
        (
            datetime(2025, 12, 30, 7, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )


def test_parse_target_time_values_preserves_explicit_timestamp_offsets() -> None:
    assert parse_target_time_values(
        ("2025-12-30T00:00:00-05:00",),
        timezone_value="America/Denver",
    ) == (
        (
            datetime(2025, 12, 30, 5, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )


def test_parse_target_time_values_supports_fixed_offset_timezones() -> None:
    assert parse_target_time_values(
        ("2025-12-30",),
        timezone_value="UTC-05:00",
    ) == (
        (
            datetime(2025, 12, 30, 5, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )
    assert parse_target_time_values(
        ("2025-12-30",),
        timezone_value="-05:00",
    ) == (
        (
            datetime(2025, 12, 30, 5, 0, 0, tzinfo=UTC),
            TemporalPrecision.TIMESTAMP,
        ),
    )


def test_parse_target_time_values_rejects_unknown_timezones() -> None:
    with pytest.raises(ValueError, match="unknown timezone"):
        parse_target_time_values(("2025-12-30",), timezone_value="Mars/Base")
