"""Binance PDF balance extraction."""

from __future__ import annotations

import re
from pathlib import Path

from crypto_reconciliation.adapters.sources.pdf_balance_common import (
    decimal_text,
    normalize_whitespace,
    parse_balance_lines,
)

BINANCE_PERIOD_PATTERN = re.compile(
    r"Report Period:\s+(?P<start>[A-Za-z]+\s+\d{2},\s+\d{4})\s+-\s+(?P<end>[A-Za-z]+\s+\d{2},\s+\d{4})"
)
BINANCE_TOTAL_PATTERN = re.compile(r"Total Account Value:?\s+(?P<value>[0-9.]+)\s+(?P<currency>[A-Z]{3})")
BINANCE_WALLETS_PATTERN = re.compile(
    r"(?:Wallet Balance\s+)?Funding\s+Spot & Margin\s+Futures\s+Options\s+Earn\s+"
    r"(?P<funding>[0-9.]+)\s+USD\s+"
    r"(?P<spot_margin>[0-9.]+)\s+USD\s+"
    r"(?P<futures>[0-9.]+)\s+USD\s+"
    r"(?P<options>[0-9.]+)\s+USD\s+"
    r"(?P<earn>[0-9.]+)\s+USD"
)


def match_pdf_statement(pdf_path: Path, text: str) -> int:
    normalized = normalize_whitespace(text)
    if pdf_path.name.startswith("AccountStatementPeriod_"):
        return 100
    if "binance" in pdf_path.name.lower():
        return 90
    if BINANCE_PERIOD_PATTERN.search(normalized) and BINANCE_TOTAL_PATTERN.search(normalized):
        return 80
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    period_match = BINANCE_PERIOD_PATTERN.search(normalized)
    total_match = BINANCE_TOTAL_PATTERN.search(normalized)
    wallet_match = BINANCE_WALLETS_PATTERN.search(normalized)
    if period_match is None or total_match is None or wallet_match is None:
        return parse_balance_lines(text, "binance", pdf_file)
    as_of = period_match.group("end")
    rows = [
        {
            "source": "Binance",
            "account": "Binance",
            "wallet": "Consolidated",
            "balance_kind": "account_total_value",
            "asset": "",
            "quantity": "",
            "staked_quantity": "",
            "value_amount": decimal_text(total_match.group("value"), places="0.00"),
            "value_currency": total_match.group("currency"),
            "price_amount": "",
            "price_currency": "",
            "as_of": as_of,
            "pdf_file": pdf_file,
            "notes": "Total Binance account value from account statement PDF",
        }
    ]
    for wallet_key, label in (
        ("funding", "Funding"),
        ("spot_margin", "Spot & Margin"),
        ("futures", "Futures"),
        ("options", "Options"),
        ("earn", "Earn"),
    ):
        rows.append(
            {
                "source": "Binance",
                "account": "Binance",
                "wallet": label,
                "balance_kind": "wallet_total_value",
                "asset": "",
                "quantity": "",
                "staked_quantity": "",
                "value_amount": decimal_text(wallet_match.group(wallet_key), places="0.00"),
                "value_currency": "USD",
                "price_amount": "",
                "price_currency": "",
                "as_of": as_of,
                "pdf_file": pdf_file,
                "notes": "Wallet total from Binance account statement PDF",
            }
        )
    return rows
