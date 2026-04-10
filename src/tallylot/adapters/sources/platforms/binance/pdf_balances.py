"""Binance PDF balance extraction."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.binance.statement_evidence import (
    extract_pdf_balances as _extract_statement_balances,
    match_statement_document as _match_statement_document,
    parse_statement_document as _parse_statement_document,
)
from tallylot.ports.evidence import StatementDocumentParseResult


def match_statement_document(pdf_path: Path, text: str) -> int:
    return _match_statement_document(pdf_path, text)


def parse_statement_document(pdf_path: Path, text: str) -> StatementDocumentParseResult:
    return _parse_statement_document(pdf_path, text)


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    return _extract_statement_balances(text, pdf_file)
