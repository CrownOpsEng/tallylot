"""Binance field parsing helpers."""

from __future__ import annotations

import re
from decimal import Decimal

from tallylot.domain.value_objects import parse_decimal


def split_pair(pair: str) -> tuple[str, str]:
    quote_candidates = (
        "USDT",
        "USDC",
        "BUSD",
        "BTC",
        "ETH",
        "BNB",
        "EUR",
        "USD",
        "CAD",
    )
    for quote in quote_candidates:
        if pair.endswith(quote) and len(pair) > len(quote):
            return pair[: -len(quote)], quote
    return "", ""


def amount_with_asset(value: str) -> tuple[Decimal | None, str]:
    match = re.fullmatch(r"\s*([+-]?[0-9]*\.?[0-9]+)\s*([A-Za-z0-9]+)\s*", value or "")
    if match is None:
        return parse_decimal((value or "").strip()), ""
    amount = parse_decimal(match.group(1))
    return amount, match.group(2).upper()


def row_change(row: dict[str, str]) -> Decimal:
    return parse_decimal((row.get("Change") or "").strip()) or Decimal("0")
