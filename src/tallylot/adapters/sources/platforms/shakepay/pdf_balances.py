"""Shakepay PDF balance extraction."""

from __future__ import annotations

import re
from pathlib import Path

from tallylot.adapters.sources.pdf_balance_common import (
    decimal_text,
    normalize_whitespace,
)
from tallylot.adapters.sources.platforms.shakepay.statement_evidence import (
    extract_pdf_balances as _extract_statement_balances,
    match_statement_document as _match_statement_document,
    parse_statement_document as _parse_statement_document,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)

SHAKEPAY_OPENING_PATTERN = re.compile(
    r"Opening market value\s+\$?(?P<value>[0-9,]+\.[0-9]{2})\s+\$?[0-9,]+\.[0-9]{2}\s+"
    r"\(as of (?P<as_of>[0-9-]+\s+[0-9:]+\s+[A-Z]{3})\)"
)
SHAKEPAY_CLOSING_PATTERN = re.compile(
    r"Closing market value at year end\s+\$?(?P<value>[0-9,]+\.[0-9]{2})\s+\$?[0-9,]+\.[0-9]{2}\s+"
    r"\(as of (?P<as_of>[0-9-]+\s+[0-9:]+\s+[A-Z]{3})\)"
)
SHAKEPAY_LEGACY_OPENING_AS_OF_PATTERN = re.compile(
    r"Opening market value\s+\(as of (?P<as_of>[0-9-]+\s+[0-9:]+\s+EST)\)"
)
SHAKEPAY_LEGACY_OPENING_VALUE_PATTERN = re.compile(
    r"For the year \(\$\)\s+Since account opening \(\$\)\s+\$(?P<value>[0-9,]+\.[0-9]{2})"
)
SHAKEPAY_LEGACY_CLOSING_PATTERN = re.compile(
    r"Closing market value at year end\s+\$?(?P<value>[0-9,]+\.[0-9]{2})"
)
SHAKEPAY_YEAR_PATTERN = re.compile(
    r"For the year ending on December 31,\s+(?P<year>\d{4})"
)


def match_statement_document(pdf_path: Path, text: str) -> int:
    monthly_score = _match_statement_document(pdf_path, text)
    if monthly_score > 0:
        return monthly_score
    normalized = normalize_whitespace(text).lower()
    file_name = pdf_path.name.lower()
    if "shakepay" in file_name and "performance report" in file_name:
        return 90
    if (
        "performance report" in normalized
        and "opening market value" in normalized
        and "closing market value at year end" in normalized
    ):
        return 80
    return 0


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    if _match_statement_document(Path(pdf_file), text) > 0:
        return _extract_statement_balances(text, pdf_file)
    return _extract_annual_market_value_rows(text, pdf_file)


def parse_statement_document(pdf_path: Path, text: str) -> StatementDocumentParseResult:
    if _match_statement_document(pdf_path, text) > 0:
        return _parse_statement_document(pdf_path, text)
    annual_rows = _extract_annual_market_value_rows(text, pdf_path.name)
    if not annual_rows:
        return StatementDocumentParseResult(
            pdf_file=pdf_path.name,
            recognized=False,
            statement_as_of_at=None,
            rows=(),
        )
    return StatementDocumentParseResult(
        pdf_file=pdf_path.name,
        recognized=True,
        statement_as_of_at=None,
        rows=tuple(_annual_row_to_statement_document_row(row) for row in annual_rows),
    )


def _extract_annual_market_value_rows(text: str, pdf_file: str) -> list[dict[str, str]]:
    normalized = normalize_whitespace(text)
    opening_match = SHAKEPAY_OPENING_PATTERN.search(normalized)
    closing_match = SHAKEPAY_CLOSING_PATTERN.search(normalized)
    if opening_match is not None and closing_match is not None:
        opening_value = opening_match.group("value")
        opening_as_of = opening_match.group("as_of")
        closing_value = closing_match.group("value")
        closing_as_of = closing_match.group("as_of")
    else:
        legacy_opening_as_of_match = SHAKEPAY_LEGACY_OPENING_AS_OF_PATTERN.search(
            normalized
        )
        legacy_opening_value_match = SHAKEPAY_LEGACY_OPENING_VALUE_PATTERN.search(
            normalized
        )
        legacy_closing_match = SHAKEPAY_LEGACY_CLOSING_PATTERN.search(normalized)
        year_match = SHAKEPAY_YEAR_PATTERN.search(normalized)
        if (
            legacy_opening_as_of_match is None
            or legacy_opening_value_match is None
            or legacy_closing_match is None
            or year_match is None
        ):
            return []
        opening_value = legacy_opening_value_match.group("value")
        opening_as_of = legacy_opening_as_of_match.group("as_of")
        closing_value = legacy_closing_match.group("value")
        closing_as_of = f"{year_match.group('year')}-12-31 23:59 EST"
    return [
        {
            "source": "Shakepay",
            "account": "Shakepay",
            "wallet": "Personal",
            "balance_kind": "opening_market_value",
            "asset": "",
            "quantity": "",
            "staked_quantity": "",
            "value_amount": decimal_text(opening_value, places="0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": opening_as_of,
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
            "value_amount": decimal_text(closing_value, places="0.00"),
            "value_currency": "CAD",
            "price_amount": "",
            "price_currency": "",
            "as_of": closing_as_of,
            "pdf_file": pdf_file,
            "notes": "Closing market value from Shakepay performance report",
        },
    ]


def _annual_row_to_statement_document_row(
    row: dict[str, str],
) -> StatementDocumentBalanceRow:
    return StatementDocumentBalanceRow(
        source=row["source"],
        account=row["account"],
        wallet=row["wallet"],
        balance_kind=row["balance_kind"],
        asset=row["asset"],
        quantity=None,
        as_of_at=None,
        as_of_precision=TemporalPrecision.TIMESTAMP,
        pdf_file=row["pdf_file"],
        as_of_text=row["as_of"],
        notes=row["notes"],
        value_amount=row["value_amount"],
        value_currency=row["value_currency"],
    )
