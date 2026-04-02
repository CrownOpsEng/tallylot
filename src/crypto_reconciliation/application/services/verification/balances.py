"""Balance delta helpers for verification export comparison."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal


def build_balance_map(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    amounts: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        amounts[row["Ticker"]] += Decimal(row["Amount"])
    return dict(amounts)


def build_exchange_balance_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], Decimal]:
    amounts: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        amounts[(row["Exchange"], row["Currency"])] += Decimal(row["Amount"])
    return dict(amounts)


def compare_balance_maps(
    previous: dict[str, Decimal],
    current: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ticker in sorted(set(previous) | set(current)):
        previous_amount = previous.get(ticker, Decimal("0"))
        current_amount = current.get(ticker, Decimal("0"))
        difference = current_amount - previous_amount
        if difference == Decimal("0"):
            continue
        rows.append(
            {
                "ticker": ticker,
                "reference_amount": decimal_text(previous_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def compare_exchange_balance_maps(
    previous: dict[tuple[str, str], Decimal],
    current: dict[tuple[str, str], Decimal],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for exchange, currency in sorted(set(previous) | set(current)):
        previous_amount = previous.get((exchange, currency), Decimal("0"))
        current_amount = current.get((exchange, currency), Decimal("0"))
        difference = current_amount - previous_amount
        if difference == Decimal("0"):
            continue
        rows.append(
            {
                "exchange": exchange,
                "currency": currency,
                "reference_amount": decimal_text(previous_amount),
                "current_amount": decimal_text(current_amount),
                "difference": decimal_text(difference),
            }
        )
    return rows


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000000")), "f")
