#!/usr/bin/env python3

"""Shared normalization helpers for canonical event construction."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from script_common import decimal_or_zero, decimal_text

CANONICAL_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _canonical_timestamp(value: str, *, label: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError(f"Blank {label} is not allowed")
    try:
        return datetime.strptime(text, CANONICAL_TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"{label} must use {CANONICAL_TIMESTAMP_FORMAT}; got {value!r}"
        ) from exc


def attach_fee_to_event(
    event: dict[str, str],
    *,
    fee_amount: str | Decimal,
    fee_asset: str,
) -> dict[str, str]:
    fee_asset_text = fee_asset.strip().upper()
    fee_decimal = fee_amount if isinstance(fee_amount, Decimal) else decimal_or_zero(fee_amount)
    if fee_decimal <= 0 or not fee_asset_text:
        return event

    updated = dict(event)
    existing_value = updated.get("fee_amount", "0")
    existing_fee_amount = existing_value if isinstance(existing_value, Decimal) else decimal_or_zero(existing_value)
    existing_fee_asset = (updated.get("fee_asset") or "").strip().upper()
    if existing_fee_amount > 0 and (
        existing_fee_amount != fee_decimal or (existing_fee_asset and existing_fee_asset != fee_asset_text)
    ):
        raise ValueError(
            "Event already carries a conflicting fee; adapters must resolve the fee before attaching it."
        )
    updated["fee_amount"] = decimal_text(fee_decimal)
    updated["fee_asset"] = fee_asset_text
    return updated


def attach_fee_to_event_list(
    events: list[dict[str, str]],
    *,
    fee_amount: str | Decimal,
    fee_asset: str,
    target_event_id: str | None = None,
    timestamp: str | None = None,
    timestamp_tolerance_seconds: int = 0,
    standalone_event: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    fee_decimal = fee_amount if isinstance(fee_amount, Decimal) else decimal_or_zero(fee_amount)
    fee_asset_text = fee_asset.strip().upper()
    if fee_decimal <= 0 or not fee_asset_text:
        return list(events)

    if timestamp_tolerance_seconds < 0:
        raise ValueError("timestamp_tolerance_seconds must be non-negative")

    if not events:
        if standalone_event is not None:
            return [standalone_event]
        raise ValueError(
            "Attached fees require a single unambiguous target event; emit a standalone fee event instead."
        )

    matches: list[int] = []
    if target_event_id is not None:
        matches = [index for index, event in enumerate(events) if event.get("event_id") == target_event_id]
    elif timestamp is not None:
        target_timestamp = _canonical_timestamp(timestamp, label="fee timestamp")
        for index, event in enumerate(events):
            event_timestamp = (event.get("timestamp") or "").strip()
            if not event_timestamp:
                continue
            delta_seconds = abs(
                (_canonical_timestamp(event_timestamp, label="event timestamp") - target_timestamp).total_seconds()
            )
            if delta_seconds <= timestamp_tolerance_seconds:
                matches.append(index)
    elif len(events) == 1:
        matches = [0]

    if len(matches) != 1:
        if standalone_event is not None:
            return [*events, standalone_event]
        raise ValueError(
            "Attached fees require a single unambiguous target event; emit a standalone fee event instead."
        )

    updated = list(events)
    target_index = matches[0]
    updated[target_index] = attach_fee_to_event(updated[target_index], fee_amount=fee_decimal, fee_asset=fee_asset_text)
    return updated
