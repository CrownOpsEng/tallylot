"""Balance assertion formatting helpers."""

from __future__ import annotations

from datetime import datetime

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import format_temporal_value


def format_assertion_temporal_text(
    value: datetime | None,
    precision: TemporalPrecision | None,
    *,
    label: str,
) -> str:
    """Render an optional temporal value and precision pair."""

    if value is None or precision is None:
        return ""
    return format_temporal_value(value, precision=precision, label=label)


def format_assertion_precision(precision: TemporalPrecision | None) -> str:
    """Render an optional temporal precision value."""

    return "" if precision is None else precision.value
