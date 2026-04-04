"""Shakepay PDF balance extraction."""

from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.statement_evidence import (
    extract_pdf_balances as _extract_statement_balances,
    match_statement as _match_statement,
)


def match_pdf_statement(pdf_path: Path, text: str) -> int:
    return _match_statement(pdf_path, text)


def extract_pdf_balances(text: str, pdf_file: str) -> list[dict[str, str]]:
    return _extract_statement_balances(text, pdf_file)
