"""Balance-kind normalization helpers."""

from __future__ import annotations

DEFAULT_BALANCE_KIND = "available"


def normalize_balance_kind(balance_kind: str) -> str:
    """Return a canonical non-blank balance kind."""

    return balance_kind.strip() or DEFAULT_BALANCE_KIND
