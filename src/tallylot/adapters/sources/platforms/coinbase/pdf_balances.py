"""Coinbase PDF balance extraction."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.sources.pdf_balance_common import (
    decimal_text,
    format_utc_timestamp,
    normalize_whitespace,
    parse_balance_lines,
)

PORTFOLIO_ROW_PATTERN = re.compile(
    r"(?P<asset>[A-Z0-9]+)\s+"
    r"(?P<quantity>[0-9.]+)\s+"
    r"(?P<staked>N/A|[0-9.]+)\s+"
    r"(?P<price>[0-9.,]+)\s+CAD/(?P=asset)\s+"
    r"(?P<value>[0-9.]+)\s+CAD"
)
PORTFOLIO_ROW_FALLBACK_PATTERN = re.compile(
    r"(?P<quantity>[0-9.]+)\s+"
    r"(?P<staked>N/A|[0-9.]+)\s+"
    r"(?P<price>[0-9.,]+)\s+CAD/(?P<asset>[A-Z0-9]+)\s+"
    r"(?P<value>[0-9.]+)\s+CAD"
)
COINBASE_CLOSING_CASH_PATTERN = re.compile(
    r"Closing Balance\s+(?P<balance>[0-9.,]+)\s+(?P<currency>[A-Z]{3})\s+as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
)
COINBASE_PORTFOLIO_AS_OF_PATTERN = re.compile(
    r"Portfolio summary balances are as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
)


def match_pdf_statement(pdf_path: Path, text: str) -> int:
    normalized = normalize_whitespace(text).lower()
    if "coinbase" in pdf_path.name.lower():
        return 100
    if re.match(r"^\d{4}-\d{2}-\d{2} - ", pdf_path.name):
        return 90
    if "coinbase" in normalized:
        return 80
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    rows: list[dict[str, str]] = []
    cash_match = COINBASE_CLOSING_CASH_PATTERN.search(normalized)
    if cash_match is not None:
        rows.append(
            {
                "source": "Coinbase",
                "account": "Coinbase",
                "wallet": "Coinbase Cash",
                "balance_kind": "cash_closing_balance",
                "asset": cash_match.group("currency"),
                "quantity": decimal_text(cash_match.group("balance")),
                "staked_quantity": "",
                "value_amount": "",
                "value_currency": "",
                "price_amount": "",
                "price_currency": "",
                "as_of": format_utc_timestamp(cash_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC"),
                "pdf_file": pdf_file,
                "notes": "Closing fiat balance from Coinbase statement PDF",
            }
        )
    portfolio_match = COINBASE_PORTFOLIO_AS_OF_PATTERN.search(normalized)
    if portfolio_match is None:
        return rows or parse_balance_lines(text, "coinbase", pdf_file)
    as_of = format_utc_timestamp(portfolio_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC")
    seen_assets: set[str] = set()
    for pattern in (PORTFOLIO_ROW_PATTERN, PORTFOLIO_ROW_FALLBACK_PATTERN):
        for match in pattern.finditer(normalized):
            asset = match.group("asset")
            if asset in seen_assets:
                continue
            seen_assets.add(asset)
            staked = match.group("staked")
            rows.append(
                {
                    "source": "Coinbase",
                    "account": "Coinbase",
                    "wallet": "Coinbase",
                    "balance_kind": "asset_balance",
                    "asset": asset,
                    "quantity": decimal_text(match.group("quantity")),
                    "staked_quantity": "" if staked == "N/A" else decimal_text(staked),
                    "value_amount": decimal_text(match.group("value"), places="0.00"),
                    "value_currency": "CAD",
                    "price_amount": decimal_text(match.group("price")),
                    "price_currency": "CAD",
                    "as_of": as_of,
                    "pdf_file": pdf_file,
                    "notes": "Portfolio summary asset balance from Coinbase statement PDF",
                }
            )
    return rows or parse_balance_lines(text, "coinbase", pdf_file)
