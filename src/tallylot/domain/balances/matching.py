"""Shared balance target matching helpers."""

from __future__ import annotations

from datetime import datetime

from .models import BalanceTarget

type BalanceTargetMatchKey = tuple[str, str, str, str, datetime]


def balance_target_match_key(target: BalanceTarget) -> BalanceTargetMatchKey:
    """Return the exact-instant identity for balance matching."""

    return (
        str(target.source),
        str(target.location_id),
        str(target.instrument_id),
        target.balance_kind,
        target.target_at,
    )
