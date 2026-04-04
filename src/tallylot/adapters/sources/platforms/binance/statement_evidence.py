"""Structured Binance account-statement balance parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    parse_decimal,
)

REPORT_DATE_PATTERN = re.compile(r"Report Date:?\s*(?P<report_date>\d{4}/\d{2}/\d{2})")
SECTION_HEADER_PATTERN = re.compile(r"^(?P<section>.+Top 10 Holdings)$")
ASSET_ROW_PATTERN = re.compile(
    r"^(?P<symbol>[A-Z0-9]+)\s+.+?\s+(?P<quantity>[0-9,]+\.\d+)\s+[0-9,]+\.\d+\s*/\s*[-0-9,]+\.\d+"
)
CONSOLIDATED_SECTION = "Asset Allocation Your Consolidated Top 10 Assets"
PREFERRED_WALLET_SECTIONS = {
    "Funding Top 10 Holdings",
    "Spot Top 10 Holdings",
    "Margin Top 10 Holdings",
    "Futures Top 10 Holdings",
    "Options Top 10 Holdings",
    "Earn Top 10 Holdings",
}


@dataclass(frozen=True)
class BinanceStatementBalanceRow:
    section: str
    asset_symbol: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision


@dataclass(frozen=True)
class BinanceStatementParseResult:
    pdf_file: str
    recognized: bool
    statement_as_of_at: datetime | None
    rows: tuple[BinanceStatementBalanceRow, ...]

    @property
    def as_of_at(self) -> datetime | None:
        return self.statement_as_of_at


def parse_statement_pdf(pdf_path: Path) -> BinanceStatementParseResult:
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return parse_statement_text(text, pdf_path.name)


def parse_statement_text(text: str, pdf_file: str) -> BinanceStatementParseResult:
    report_date_match = REPORT_DATE_PATTERN.search(text)
    if report_date_match is None:
        return BinanceStatementParseResult(
            pdf_file=pdf_file, recognized=False, statement_as_of_at=None, rows=()
        )
    as_of_at = _parse_report_date(report_date_match.group("report_date"))
    raw_rows = _parse_section_rows(text, as_of_at)
    preferred_rows = tuple(
        row for row in raw_rows if row.section in PREFERRED_WALLET_SECTIONS
    )
    rows = preferred_rows or tuple(
        row for row in raw_rows if row.section == CONSOLIDATED_SECTION
    )
    return BinanceStatementParseResult(
        pdf_file=pdf_file, recognized=True, statement_as_of_at=as_of_at, rows=rows
    )


def match_statement(pdf_path: Path, text: str) -> int:
    del pdf_path
    if REPORT_DATE_PATTERN.search(text) is not None and "Top 10 Holdings" in text:
        return 100
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    result = parse_statement_text(text, pdf_file)
    return [
        {
            "source": "Binance",
            "account": "Binance",
            "wallet": row.section.removesuffix(" Top 10 Holdings"),
            "balance_kind": "available",
            "asset": row.asset_symbol,
            "quantity": format_decimal(row.quantity),
            "staked_quantity": "",
            "value_amount": "",
            "value_currency": "",
            "price_amount": "",
            "price_currency": "",
            "as_of": format_temporal_value(
                row.as_of_at,
                precision=row.as_of_precision,
                label="binance statement as_of",
            ),
            "pdf_file": pdf_file,
            "notes": f"Statement-backed quantity from Binance {row.section}.",
        }
        for row in result.rows
    ]


def _parse_section_rows(
    text: str, as_of_at: datetime
) -> tuple[BinanceStatementBalanceRow, ...]:
    rows: list[BinanceStatementBalanceRow] = []
    current_section = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == CONSOLIDATED_SECTION:
            current_section = CONSOLIDATED_SECTION
            continue
        section_match = SECTION_HEADER_PATTERN.match(line)
        if section_match is not None:
            current_section = section_match.group("section")
            continue
        if not current_section:
            continue
        asset_match = ASSET_ROW_PATTERN.match(line)
        if asset_match is None:
            continue
        rows.append(
            BinanceStatementBalanceRow(
                section=current_section,
                asset_symbol=asset_match.group("symbol").strip().upper(),
                quantity=_parse_required_decimal(asset_match.group("quantity")),
                as_of_at=as_of_at,
                as_of_precision=TemporalPrecision.DATE,
            )
        )
    return tuple(rows)


def _parse_required_decimal(value: str) -> Decimal:
    parsed = parse_decimal(value.replace(",", ""))
    if parsed is None:
        raise ValueError("Binance statement quantity must be present")
    return parsed


def _parse_report_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y/%m/%d").replace(tzinfo=UTC)
