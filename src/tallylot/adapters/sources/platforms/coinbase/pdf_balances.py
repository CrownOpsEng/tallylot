"""Coinbase PDF balance extraction."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from tallylot.adapters.sources.pdf_balance_common import (
    decimal_text,
    format_utc_timestamp,
    normalize_whitespace,
    parse_balance_lines,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
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
COINBASE_CLOSING_CASH_PATTERNS = (
    re.compile(
        r"Closing Balance\s+(?P<balance>[0-9.,]+)\s+(?P<currency>[A-Z]{3})\s+as of "
        r"(?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
    ),
    re.compile(
        r"Closing Balance\s+as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)\s+"
        r"(?P<balance>[0-9.,]+)\s+(?P<currency>[A-Z]{3})"
    ),
)
COINBASE_PORTFOLIO_AS_OF_PATTERN = re.compile(
    r"Portfolio summary balances are as of (?P<as_of>[0-9:-]+\s+[0-9:]+\s+UTC)"
)


def match_statement_document(pdf_path: Path, text: str) -> int:
    normalized = normalize_whitespace(text).lower()
    if not _looks_like_statement_candidate(pdf_path.name.lower(), normalized):
        return 0
    if "account statement" in normalized:
        return 100
    if "statement" in pdf_path.name.lower():
        return 90
    if "coinbase statement" in normalized:
        return 80
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    return _extract_pdf_balances(text, pdf_file, strict=True)


def _extract_pdf_balances(
    text: str,
    pdf_file: str,
    *,
    strict: bool,
) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    rows: list[dict[str, str]] = []
    cash_match = next(
        (
            match
            for pattern in COINBASE_CLOSING_CASH_PATTERNS
            for match in (pattern.search(normalized),)
            if match is not None
        ),
        None,
    )
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
                "as_of": format_utc_timestamp(
                    cash_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC"
                ),
                "pdf_file": pdf_file,
                "notes": "Closing fiat balance from Coinbase statement PDF",
            }
        )
    portfolio_match = COINBASE_PORTFOLIO_AS_OF_PATTERN.search(normalized)
    if portfolio_match is None:
        return rows or _fallback_balance_rows(text, pdf_file, strict=strict)
    as_of = format_utc_timestamp(
        portfolio_match.group("as_of"), "%Y-%m-%d %H:%M:%S UTC"
    )
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
    return rows or _fallback_balance_rows(text, pdf_file, strict=strict)


def parse_statement_document(pdf_path: Path, text: str) -> StatementDocumentParseResult:
    normalized = normalize_whitespace(text).lower()
    if not _looks_like_balance_statement(normalized):
        return StatementDocumentParseResult(
            pdf_file=pdf_path.name,
            recognized=False,
            statement_as_of_at=None,
            rows=(),
        )
    rows = _extract_pdf_balances(text, pdf_path.name, strict=False)
    return StatementDocumentParseResult(
        pdf_file=pdf_path.name,
        recognized=True,
        statement_as_of_at=_statement_as_of(rows),
        rows=tuple(_row_to_statement_document_row(row) for row in rows),
    )


def _row_to_statement_document_row(row: dict[str, str]) -> StatementDocumentBalanceRow:
    as_of_text = row["as_of"]
    as_of_at = (
        None
        if not as_of_text
        else parse_temporal_value(as_of_text, precision=TemporalPrecision.TIMESTAMP)
    )
    return StatementDocumentBalanceRow(
        source=row["source"],
        account=row["account"],
        wallet=row["wallet"],
        balance_kind=row["balance_kind"],
        asset=row["asset"],
        quantity=parse_decimal(row["quantity"]),
        as_of_at=as_of_at,
        as_of_precision=TemporalPrecision.TIMESTAMP,
        pdf_file=row["pdf_file"],
        as_of_text=as_of_text,
        notes=row["notes"],
        staked_quantity=row["staked_quantity"],
        value_amount=row["value_amount"],
        value_currency=row["value_currency"],
        price_amount=row["price_amount"],
        price_currency=row["price_currency"],
    )


def _statement_as_of(rows: list[dict[str, str]]) -> datetime | None:
    as_of_values = [
        parse_temporal_value(row["as_of"], precision=TemporalPrecision.TIMESTAMP)
        for row in rows
        if row["as_of"]
    ]
    if not as_of_values:
        return None
    return max(as_of_values)


def _looks_like_balance_statement(normalized_text: str) -> bool:
    return "portfolio summary balances are as of" in normalized_text or any(
        pattern.search(normalized_text) is not None
        for pattern in COINBASE_CLOSING_CASH_PATTERNS
    )


def _looks_like_statement_candidate(
    pdf_name: str,
    normalized_text: str,
) -> bool:
    if not _looks_like_balance_statement(normalized_text):
        return False
    return "account statement" in normalized_text or "statement" in pdf_name


def _fallback_balance_rows(
    text: str,
    pdf_file: str,
    *,
    strict: bool,
) -> list[dict[str, str]]:
    try:
        return parse_balance_lines(text, "coinbase", pdf_file)
    except ValueError:
        if strict:
            raise
        return []
