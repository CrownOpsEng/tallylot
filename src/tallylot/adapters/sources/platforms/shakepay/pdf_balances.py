"""Shakepay PDF balance extraction."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.sources.pdf_balance_common import (
    decimal_text,
    normalize_whitespace,
    parse_balance_lines,
)

SHAKEPAY_OPENING_AS_OF_PATTERN = re.compile(r"Opening market value\s+\(as of (?P<as_of>[0-9-]+\s+[0-9:]+\s+EST)\)")
SHAKEPAY_OPENING_VALUE_PATTERN = re.compile(
    r"For the year \(\$\)\s+Since account opening \(\$\)\s+\$(?P<value>[0-9,]+\.[0-9]{2})"
)
SHAKEPAY_CLOSING_PATTERN = re.compile(r"Closing market value at year end\s+\$?(?P<value>[0-9,]+\.[0-9]{2})")
SHAKEPAY_YEAR_PATTERN = re.compile(r"For the year ending on December 31,\s+(?P<year>\d{4})")


def match_pdf_statement(pdf_path: Path, text: str) -> int:
    name = pdf_path.name.lower()
    normalized = normalize_whitespace(text).lower()
    if "shakepay" in name and "performance report" in name:
        return 100
    if "shakepay" in normalized:
        return 80
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    opening_as_of_match = SHAKEPAY_OPENING_AS_OF_PATTERN.search(normalized)
    opening_value_match = SHAKEPAY_OPENING_VALUE_PATTERN.search(normalized)
    closing_match = SHAKEPAY_CLOSING_PATTERN.search(normalized)
    year_match = SHAKEPAY_YEAR_PATTERN.search(normalized)
    if opening_as_of_match is None or opening_value_match is None or closing_match is None or year_match is None:
        return parse_balance_lines(text, "shakepay", pdf_file)
    year = year_match.group("year")
    return [
        {
            "source": "Shakepay",
            "account": "Shakepay",
            "wallet": "Personal",
            "balance_kind": "opening_market_value",
            "asset": "",
            "quantity": "",
            "staked_quantity": "",
            "value_amount": decimal_text(opening_value_match.group("value"), places="0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": opening_as_of_match.group("as_of"),
            "pdf_file": pdf_file,
            "notes": "Opening market value from Shakepay performance report",
        },
        {
            "source": "Shakepay",
            "account": "Shakepay",
            "wallet": "Personal",
            "balance_kind": "closing_market_value",
            "asset": "",
            "quantity": "",
            "staked_quantity": "",
            "value_amount": decimal_text(closing_match.group("value"), places="0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": f"{year}-12-31 23:59",
            "pdf_file": pdf_file,
            "notes": "Closing market value from Shakepay performance report",
        },
    ]
