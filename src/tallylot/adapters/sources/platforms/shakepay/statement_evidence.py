"""Structured Shakepay statement balance parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.value_objects import (
    format_decimal,
    format_temporal_value,
    parse_decimal,
)
from tallylot.ports.evidence import (
    StatementDocumentBalanceRow,
    StatementDocumentParseResult,
)

TORONTO = ZoneInfo("America/Toronto")
BALANCE_SUMMARY_PATTERN = re.compile(
    r"Balance summary \(as of (?P<as_of>\d{4}-\d{2}-\d{2} \d{2}:\d{2} (?:EST|EDT))\)"
)
BALANCE_ROW_PATTERN = re.compile(
    r"^(?P<label>[A-Za-z ]+)\s+\((?P<symbol>[A-Z]{3})\)\s+(?P<quantity>[0-9,]+\.\d+)\s+"
    r"[0-9,]+\.\d+\s+[0-9,]+\.\d+\s+[0-9,]+\.\d+$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class ShakepayStatementBalanceRow:
    asset_label: str
    asset_symbol: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    notes: str


@dataclass(frozen=True)
class ShakepayStatementParseResult:
    pdf_file: str
    recognized: bool
    statement_as_of_at: datetime | None
    rows: tuple[ShakepayStatementBalanceRow, ...]

    @property
    def as_of_at(self) -> datetime | None:
        return self.statement_as_of_at


def parse_statement_text(text: str, pdf_file: str) -> ShakepayStatementParseResult:
    as_of_match = BALANCE_SUMMARY_PATTERN.search(text)
    if as_of_match is None:
        return ShakepayStatementParseResult(
            pdf_file=pdf_file, recognized=False, statement_as_of_at=None, rows=()
        )
    as_of_at = _parse_statement_timestamp(as_of_match.group("as_of"))
    rows = tuple(
        ShakepayStatementBalanceRow(
            asset_label=match.group("label").strip(),
            asset_symbol=match.group("symbol").strip().upper(),
            quantity=_parse_required_decimal(match.group("quantity")),
            as_of_at=as_of_at,
            as_of_precision=TemporalPrecision.TIMESTAMP,
            notes="Statement-backed quantity from Shakepay monthly balance summary.",
        )
        for match in BALANCE_ROW_PATTERN.finditer(text)
    )
    return ShakepayStatementParseResult(
        pdf_file=pdf_file, recognized=True, statement_as_of_at=as_of_at, rows=rows
    )


def match_statement_document(pdf_path: Path, text: str) -> int:
    del pdf_path
    if BALANCE_SUMMARY_PATTERN.search(text) is not None:
        return 100
    return 0


def parse_statement_document(pdf_path: Path, text: str) -> StatementDocumentParseResult:
    parsed = parse_statement_text(text, pdf_path.name)
    return StatementDocumentParseResult(
        pdf_file=parsed.pdf_file,
        recognized=parsed.recognized,
        statement_as_of_at=parsed.statement_as_of_at,
        rows=tuple(
            StatementDocumentBalanceRow(
                source="Shakepay",
                account="Shakepay",
                wallet="Personal",
                balance_kind="available",
                asset=row.asset_symbol,
                quantity=row.quantity,
                as_of_at=row.as_of_at,
                as_of_precision=row.as_of_precision,
                pdf_file=parsed.pdf_file,
                raw_row_ref="page:1:Balance summary",
                notes=row.notes,
            )
            for row in parsed.rows
        ),
    )


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    result = parse_statement_document(Path(pdf_file), text)
    return [
        {
            "source": row.source,
            "account": row.account,
            "wallet": row.wallet,
            "balance_kind": row.balance_kind,
            "asset": row.asset,
            "quantity": format_decimal(row.quantity),
            "staked_quantity": "",
            "value_amount": "",
            "value_currency": "",
            "price_amount": "",
            "price_currency": "",
            "as_of": _statement_as_of_text(row),
            "pdf_file": row.pdf_file,
            "notes": row.notes,
        }
        for row in result.rows
    ]


def _statement_as_of_text(row: StatementDocumentBalanceRow) -> str:
    if row.as_of_at is None:
        return row.as_of_text
    return format_temporal_value(
        row.as_of_at,
        precision=row.as_of_precision,
        label="shakepay statement as_of",
    )


def _parse_required_decimal(value: str) -> Decimal:
    parsed = parse_decimal(value.replace(",", ""))
    if parsed is None:
        raise ValueError("Shakepay statement quantity must be present")
    return parsed


def _parse_statement_timestamp(value: str) -> datetime:
    naive_text, abbreviation = value.rsplit(" ", maxsplit=1)
    local = datetime.strptime(naive_text, "%Y-%m-%d %H:%M").replace(tzinfo=TORONTO)
    if local.tzname() != abbreviation:
        raise ValueError(f"Shakepay statement timestamp abbreviation mismatch: {value}")
    return local.astimezone(UTC)
