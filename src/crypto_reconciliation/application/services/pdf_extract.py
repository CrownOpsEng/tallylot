"""PDF balance extraction service."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from crypto_reconciliation.application.dtos import PdfBalanceExtractRequest, PdfBalanceExtractResponse
from crypto_reconciliation.domain.value_objects import format_decimal, parse_decimal
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

BALANCE_HEADER = (
    "source",
    "account",
    "wallet",
    "balance_kind",
    "asset",
    "quantity",
    "staked_quantity",
    "value_amount",
    "value_currency",
    "price_amount",
    "price_currency",
    "as_of",
    "pdf_file",
    "notes",
)
BALANCE_LINE = re.compile(r"\b([A-Z]{2,10})\b\s+(-?\d[\d,]*(?:\.\d+)?)\b")
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
SHAKEPAY_OPENING_VALUE_PATTERN = re.compile(
    r"For the year \(\$\)\s+Since account opening \(\$\)\s+\$(?P<value>[0-9,]+\.[0-9]{2})"
)
SHAKEPAY_CLOSING_PATTERN = re.compile(r"Closing market value at year end\s+\$?(?P<value>[0-9,]+\.[0-9]{2})")
SHAKEPAY_YEAR_PATTERN = re.compile(r"For the year ending on December 31,\s+(?P<year>\d{4})")
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


class PdfBalanceExtractionService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: PdfBalanceExtractRequest) -> PdfBalanceExtractResponse:
        reader = PdfReader(str(request.pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        statement_kind = _detect_statement_kind(request.pdf_path, text, request.statement_kind)
        parser = _STATEMENT_PARSERS[statement_kind]
        rows = parser(text, request.pdf_path.name)
        self._artifacts.write_rows(request.output_path, BALANCE_HEADER, rows)
        return PdfBalanceExtractResponse(
            output_path=request.output_path,
            row_count=len(rows),
            statement_kind=statement_kind,
        )


def _detect_statement_kind(pdf_path: Path, text: str, requested: str | None) -> str:
    if requested:
        if requested not in _STATEMENT_PARSERS:
            raise ValueError(f"unsupported statement kind: {requested}")
        return requested
    name = pdf_path.name.lower()
    if "coinbase" in name or re.match(r"^\d{4}-\d{2}-\d{2} - ", pdf_path.name):
        return "coinbase"
    if "binance" in name or pdf_path.name.startswith("AccountStatementPeriod_"):
        return "binance"
    if "shakepay" in name and "performance report" in name:
        return "shakepay"
    lowered = text.lower()
    for name in ("coinbase", "binance", "shakepay"):
        if name in lowered:
            return name
    raise ValueError("unable to detect supported statement kind from PDF text")


def _parse_balance_lines(text: str, statement_kind: str, pdf_file: str) -> list[dict[str, str]]:
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
        raise ValueError(f"no balance rows were extracted from the {statement_kind} PDF")
    return rows


def _coinbase_rows(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = _normalize_whitespace(text)
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
                "quantity": _decimal_text(cash_match.group("balance")),
                "staked_quantity": "",
                "value_amount": "",
                "value_currency": "",
                "price_amount": "",
                "price_currency": "",
                "as_of": _format_utc_timestamp(cash_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC"),
                "pdf_file": pdf_file,
                "notes": "Closing fiat balance from Coinbase statement PDF",
            }
        )
    portfolio_match = COINBASE_PORTFOLIO_AS_OF_PATTERN.search(normalized)
    if portfolio_match is None:
        return rows or _parse_balance_lines(text, "coinbase", pdf_file)
    as_of = _format_utc_timestamp(portfolio_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC")
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
                    "quantity": _decimal_text(match.group("quantity")),
                    "staked_quantity": "" if staked == "N/A" else _decimal_text(staked),
                    "value_amount": _decimal_text(match.group("value"), places="0.00"),
                    "value_currency": "CAD",
                    "price_amount": _decimal_text(match.group("price")),
                    "price_currency": "CAD",
                    "as_of": as_of,
                    "pdf_file": pdf_file,
                    "notes": "Portfolio summary asset balance from Coinbase statement PDF",
                }
            )
    return rows or _parse_balance_lines(text, "coinbase", pdf_file)


def _binance_rows(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = _normalize_whitespace(text)
    period_match = BINANCE_PERIOD_PATTERN.search(normalized)
    total_match = BINANCE_TOTAL_PATTERN.search(normalized)
    wallet_match = BINANCE_WALLETS_PATTERN.search(normalized)
    if period_match is None or total_match is None or wallet_match is None:
        return _parse_balance_lines(text, "binance", pdf_file)
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
            "value_amount": _decimal_text(total_match.group("value"), places="0.00"),
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
                "value_amount": _decimal_text(wallet_match.group(wallet_key), places="0.00"),
                "value_currency": "USD",
                "price_amount": "",
                "price_currency": "",
                "as_of": as_of,
                "pdf_file": pdf_file,
                "notes": "Wallet total from Binance account statement PDF",
            }
        )
    return rows


def _shakepay_rows(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = _normalize_whitespace(text)
    opening_as_of_match = SHAKEPAY_OPENING_AS_OF_PATTERN.search(normalized)
    opening_value_match = SHAKEPAY_OPENING_VALUE_PATTERN.search(normalized)
    closing_match = SHAKEPAY_CLOSING_PATTERN.search(normalized)
    year_match = SHAKEPAY_YEAR_PATTERN.search(normalized)
    if opening_as_of_match is None or opening_value_match is None or closing_match is None or year_match is None:
        return _parse_balance_lines(text, "shakepay", pdf_file)
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
            "value_amount": _decimal_text(opening_value_match.group("value"), places="0.00"),
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
            "value_amount": _decimal_text(closing_match.group("value"), places="0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": f"{year}-12-31 23:59",
            "pdf_file": pdf_file,
            "notes": "Closing market value from Shakepay performance report",
        },
    ]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _decimal_text(value: str, *, places: str | None = None) -> str:
    parsed = parse_decimal(value)
    if parsed is None:
        return ""
    if places is not None:
        return format(parsed.quantize(Decimal(places)), "f")
    return format_decimal(parsed)


def _format_utc_timestamp(value: str, time_format: str) -> str:
    return datetime.strptime(value, time_format).replace(tzinfo=UTC).strftime("%Y-%m-%d %H:%M:%S")


_STATEMENT_PARSERS: dict[str, Callable[[str, str], list[dict[str, str]]]] = {
    "coinbase": _coinbase_rows,
    "binance": _binance_rows,
    "shakepay": _shakepay_rows,
}
