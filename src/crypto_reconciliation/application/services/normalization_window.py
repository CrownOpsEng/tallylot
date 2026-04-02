"""Helpers for explicit normalization windows."""

from __future__ import annotations

from crypto_reconciliation.domain.models import CanonicalEvent
from crypto_reconciliation.domain.value_objects import parse_timestamp


def filter_events_by_window(
    events: tuple[CanonicalEvent, ...],
    *,
    window_start: str | None,
    window_end: str | None,
) -> tuple[tuple[CanonicalEvent, ...], int]:
    if not window_start and not window_end:
        return events, 0
    start_dt = parse_timestamp(window_start) if window_start else None
    end_dt = parse_timestamp(window_end) if window_end else None
    filtered: list[CanonicalEvent] = []
    excluded_count = 0
    for event in events:
        if start_dt is not None and event.timestamp < start_dt:
            excluded_count += 1
            continue
        if end_dt is not None and event.timestamp > end_dt:
            excluded_count += 1
            continue
        filtered.append(event)
    return tuple(filtered), excluded_count
