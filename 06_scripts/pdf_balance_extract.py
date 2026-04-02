#!/usr/bin/env python3

"""Deterministically extract statement balances from supported PDF exports."""

from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Callable, Sequence

from coinbase_common import BALANCE_HEADERS, coinbase_balance_rows_from_text
from script_common import decimal_text, extract_pdf_text, normalize_whitespace, parse_decimal, write_csv_rows


Extractor = Callable[[str, str], list[dict[str, str]]]

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
SHAKEPAY_OPENING_AS_OF_PATTERN = re.compile(r"Opening market value\s+\(as of (?P<as_of>[0-9-]+\s+[0-9:]+\s+EST)\)")
SHAKEPAY_OPENING_VALUE_PATTERN = re.compile(r"For the year \(\$\)\s+Since account opening \(\$\)\s+\$(?P<value>[0-9,]+\.[0-9]{2})")
SHAKEPAY_CLOSING_PATTERN = re.compile(r"Closing market value at year end\s+\$?(?P<value>[0-9,]+\.[0-9]{2})")
SHAKEPAY_YEAR_PATTERN = re.compile(r"For the year ending on December 31,\s+(?P<year>\d{4})")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("auto", "coinbase", "binance", "shakepay"), default="auto")
    parser.add_argument("--pdf", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def binance_balance_rows_from_text(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    period_match = BINANCE_PERIOD_PATTERN.search(normalized)
    total_match = BINANCE_TOTAL_PATTERN.search(normalized)
    wallet_match = BINANCE_WALLETS_PATTERN.search(normalized)
    if period_match is None or total_match is None or wallet_match is None:
        return []
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
            "value_amount": decimal_text(parse_decimal(total_match.group("value")) or Decimal("0"), "0.00"),
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
                "value_amount": decimal_text(parse_decimal(wallet_match.group(wallet_key)) or Decimal("0"), "0.00"),
                "value_currency": "USD",
                "price_amount": "",
                "price_currency": "",
                "as_of": as_of,
                "pdf_file": pdf_file,
                "notes": "Wallet total from Binance account statement PDF",
            }
        )
    return rows


def shakepay_balance_rows_from_text(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    opening_as_of_match = SHAKEPAY_OPENING_AS_OF_PATTERN.search(normalized)
    opening_value_match = SHAKEPAY_OPENING_VALUE_PATTERN.search(normalized)
    closing_match = SHAKEPAY_CLOSING_PATTERN.search(normalized)
    year_match = SHAKEPAY_YEAR_PATTERN.search(normalized)
    if opening_as_of_match is None or opening_value_match is None or closing_match is None or year_match is None:
        return []
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
            "value_amount": decimal_text(parse_decimal(opening_value_match.group("value")) or Decimal("0"), "0.00"),
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
            "value_amount": decimal_text(parse_decimal(closing_match.group("value")) or Decimal("0"), "0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": f"{year}-12-31 23:59",
            "pdf_file": pdf_file,
            "notes": "Closing market value from Shakepay performance report",
        },
    ]


def detect_extractor(pdf_path: Path) -> tuple[str, Extractor]:
    name = pdf_path.name.lower()
    if "coinbase" in name or re.match(r"^\d{4}-\d{2}-\d{2} - ", pdf_path.name):
        return "coinbase", coinbase_balance_rows_from_text
    if pdf_path.name.startswith("AccountStatementPeriod_"):
        return "binance", binance_balance_rows_from_text
    if "shakepay" in name and "performance report" in name:
        return "shakepay", shakepay_balance_rows_from_text
    raise ValueError(f"Unable to deterministically select a balance extractor for {pdf_path.name}")


def extractor_for_source(source: str) -> Extractor:
    if source == "coinbase":
        return coinbase_balance_rows_from_text
    if source == "binance":
        return binance_balance_rows_from_text
    if source == "shakepay":
        return shakepay_balance_rows_from_text
    raise ValueError(source)


def extract_pdf_balances(source: str, pdf_paths: list[Path], output: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    extracted_files: list[str] = []
    for pdf_path in pdf_paths:
        extractor = extractor_for_source(source) if source != "auto" else detect_extractor(pdf_path)[1]
        pdf_rows = extractor(extract_pdf_text(pdf_path), pdf_path.name)
        if not pdf_rows:
            raise ValueError(f"No balance rows extracted from {pdf_path}")
        rows.extend(pdf_rows)
        extracted_files.append(pdf_path.name)
    write_csv_rows(output, list(BALANCE_HEADERS), rows)
    return {
        "pdf_files": extracted_files,
        "balance_rows": len(rows),
        "output": str(output),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    summary = extract_pdf_balances(args.source, args.pdf, args.output)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
