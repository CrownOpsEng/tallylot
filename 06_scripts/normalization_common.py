#!/usr/bin/env python3

"""Shared normalization helpers for canonical event construction."""

from __future__ import annotations

from decimal import Decimal

from script_common import decimal_or_zero, decimal_text


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
    existing_fee_amount = decimal_or_zero(updated.get("fee_amount", "0"))
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
    index: int = 0,
) -> list[dict[str, str]]:
    if not events:
        return events
    updated = list(events)
    updated[index] = attach_fee_to_event(updated[index], fee_amount=fee_amount, fee_asset=fee_asset)
    return updated
