"""Shared PDF balance parsing helpers for source adapters."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.value_objects import format_decimal, parse_decimal

BALANCE_LINE = re.compile(r"\b([A-Z]{2,10})\b\s+(-?\d[\d,]*(?:\.\d+)?)\b")


def parse_balance_lines(
    text: str, statement_kind: str, pdf_file: str
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        match = BALANCE_LINE.search(line.strip())
        if match is None:
            continue
        rows.append(
            {
                "source": statement_kind.capitalize(),
                "account": statement_kind.capitalize(),
                "wallet": statement_kind.capitalize(),
                "balance_kind": "asset_balance",
                "asset": match.group(1),
                "quantity": match.group(2).replace(",", ""),
                "staked_quantity": "",
                "value_amount": "",
                "value_currency": "",
                "price_amount": "",
                "price_currency": "",
                "as_of": "",
                "pdf_file": pdf_file,
                "notes": f"Balance row extracted from {statement_kind} PDF line: {line.strip()}",
            }
        )
    if not rows:
        raise ValueError(
            f"no balance rows were extracted from the {statement_kind} PDF"
        )
    return rows


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def decimal_text(value: str, *, places: str | None = None) -> str:
    parsed = parse_decimal(value.replace(",", ""))
    if parsed is None:
        return ""
    if places is not None:
        return format(parsed.quantize(Decimal(places)), "f")
    return format_decimal(parsed)


def format_utc_timestamp(value: str, time_format: str) -> str:
    return (
        datetime.strptime(value, time_format)
        .replace(tzinfo=UTC)
        .strftime("%Y-%m-%d %H:%M:%S")
    )
